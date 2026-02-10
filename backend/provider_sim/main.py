"""Provider Simulator - Fake payment processors with failure injection and webhooks."""

import os
import uuid
import hmac
import hashlib
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

import sys
sys.path.insert(0, "/app/shared")

from shared.file_store import FileStore
from shared.correlation import get_correlation_id
from shared.middleware import CorrelationMiddleware
from failure_injection import FailureConfig, PROVIDER_PROFILES, DECLINE_REASONS

import httpx

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("provider-sim")

app = FastAPI(title="PayRail Provider Simulator", version="1.0.0")
app.add_middleware(CorrelationMiddleware)

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
PROVIDERS_DIR = os.path.join(DATA_DIR, "providers")
SETTLEMENT_DIR = os.path.join(DATA_DIR, "settlement")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "whsec_payrail_demo_secret_key_2026")
WEBHOOK_CALLBACK_URL = os.environ.get("WEBHOOK_CALLBACK_URL", "http://api-gateway:8026/webhooks/provider")
SEED = int(os.environ.get("SEED", 42))

rng = random.Random(SEED)


def _sim_state_path(provider_id: str) -> str:
    return os.path.join(PROVIDERS_DIR, f"{provider_id}_sim.json")


def _read_sim_state(provider_id: str) -> dict:
    return FileStore.read_json(_sim_state_path(provider_id), default={
        "provider_id": provider_id,
        "total_requests": 0,
        "total_successes": 0,
        "total_failures": 0,
        "last_request_at": None,
    })


def get_provider_config(provider_id: str) -> FailureConfig:
    state = _read_sim_state(provider_id)
    if "failure_config" in state:
        return FailureConfig(**state["failure_config"])
    # Backward-compat: fall back to legacy state file if present
    legacy_path = os.path.join(PROVIDERS_DIR, f"{provider_id}_state.json")
    legacy = FileStore.read_json(legacy_path, default={})
    if "failure_config" in legacy:
        return FailureConfig(**legacy["failure_config"])
    return PROVIDER_PROFILES.get(provider_id, FailureConfig())


def save_provider_state(provider_id: str, updates: dict):
    state_path = _sim_state_path(provider_id)
    state = _read_sim_state(provider_id)
    state.update(updates)
    FileStore.write_json(state_path, state)


def sign_webhook(payload: str) -> str:
    signature = hmac.new(
        WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


async def send_webhook(event_type: str, data: dict, provider_id: str):
    payload = json.dumps({
        "id": f"whevt_{uuid.uuid4().hex[:12]}",
        "type": event_type,
        "provider": provider_id,
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
    })
    signature = sign_webhook(payload)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                WEBHOOK_CALLBACK_URL,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Correlation-Id": get_correlation_id(),
                },
                timeout=10.0,
            )
        logger.info(f"Webhook sent: {event_type} for provider {provider_id}")

        # Duplicate webhook injection
        config = get_provider_config(provider_id)
        if rng.random() < config.duplicate_webhook_rate:
            logger.info(f"Injecting duplicate webhook: {event_type}")
            await asyncio.sleep(0.5)
            async with httpx.AsyncClient() as client:
                await client.post(
                    WEBHOOK_CALLBACK_URL,
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Correlation-Id": get_correlation_id(),
                    },
                    timeout=10.0,
                )
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")


# === Request/Response Models ===

class AuthorizeRequest(BaseModel):
    payment_id: str
    amount: int
    currency: str = "USD"
    pan: str
    expiry: str
    merchant_id: str
    correlation_id: Optional[str] = None


class AuthorizeResponse(BaseModel):
    success: bool
    provider_ref: Optional[str] = None
    decline_reason: Optional[str] = None
    provider_id: str


class CaptureRequest(BaseModel):
    payment_id: str
    provider_ref: str
    amount: int
    correlation_id: Optional[str] = None


class CaptureResponse(BaseModel):
    success: bool
    provider_ref: str
    provider_id: str


class RefundRequest(BaseModel):
    payment_id: str
    provider_ref: str
    amount: int
    correlation_id: Optional[str] = None


class RefundResponse(BaseModel):
    success: bool
    refund_ref: Optional[str] = None
    provider_id: str


class InjectFailureRequest(BaseModel):
    timeout_rate: Optional[float] = None
    decline_rate: Optional[float] = None
    error_rate: Optional[float] = None
    duplicate_webhook_rate: Optional[float] = None
    settlement_mismatch_rate: Optional[float] = None
    latency_ms_min: Optional[int] = None
    latency_ms_max: Optional[int] = None


# === Endpoints ===

@app.post("/providers/{provider_id}/authorize", response_model=AuthorizeResponse)
async def authorize(provider_id: str, req: AuthorizeRequest, background_tasks: BackgroundTasks):
    config = get_provider_config(provider_id)

    # Simulate latency
    latency = rng.randint(config.latency_ms_min, config.latency_ms_max)
    await asyncio.sleep(latency / 1000.0)

    # Simulate timeout
    if rng.random() < config.timeout_rate:
        logger.warning(f"Injected timeout for {provider_id}")
        await asyncio.sleep(15)
        raise HTTPException(status_code=504, detail="Gateway timeout")

    # Simulate server error
    if rng.random() < config.error_rate:
        logger.warning(f"Injected 500 error for {provider_id}")
        state = _read_sim_state(provider_id)
        save_provider_state(provider_id, {
            "total_requests": state.get("total_requests", 0) + 1,
            "total_failures": state.get("total_failures", 0) + 1,
            "last_request_at": datetime.utcnow().isoformat(),
        })
        raise HTTPException(status_code=500, detail="Internal provider error")

    # Simulate decline
    if rng.random() < config.decline_rate:
        reasons = DECLINE_REASONS.get(provider_id, ["declined"])
        reason = rng.choice(reasons)
        logger.info(f"Declined payment {req.payment_id}: {reason}")
        state = _read_sim_state(provider_id)
        save_provider_state(provider_id, {
            "total_requests": state.get("total_requests", 0) + 1,
            "total_failures": state.get("total_failures", 0) + 1,
            "last_request_at": datetime.utcnow().isoformat(),
        })
        background_tasks.add_task(
            send_webhook, "payment.declined", {
                "payment_id": req.payment_id,
                "decline_reason": reason,
            }, provider_id
        )
        return AuthorizeResponse(
            success=False, decline_reason=reason, provider_id=provider_id
        )

    # Success
    ref_prefix = "ch_" if provider_id == "providerA" else "PSP_"
    provider_ref = f"{ref_prefix}{uuid.uuid4().hex[:12]}"

    state = _read_sim_state(provider_id)
    save_provider_state(provider_id, {
        "total_requests": state.get("total_requests", 0) + 1,
        "total_successes": state.get("total_successes", 0) + 1,
        "last_request_at": datetime.utcnow().isoformat(),
    })

    background_tasks.add_task(
        send_webhook, "payment.authorized", {
            "payment_id": req.payment_id,
            "provider_ref": provider_ref,
            "amount": req.amount,
            "currency": req.currency,
        }, provider_id
    )

    logger.info(f"Authorized {req.payment_id} -> {provider_ref}")
    return AuthorizeResponse(
        success=True, provider_ref=provider_ref, provider_id=provider_id
    )


@app.post("/providers/{provider_id}/capture", response_model=CaptureResponse)
async def capture(provider_id: str, req: CaptureRequest, background_tasks: BackgroundTasks):
    config = get_provider_config(provider_id)
    latency = rng.randint(config.latency_ms_min, config.latency_ms_max)
    await asyncio.sleep(latency / 1000.0)

    if rng.random() < config.error_rate:
        raise HTTPException(status_code=500, detail="Capture failed at provider")

    background_tasks.add_task(
        send_webhook, "payment.captured", {
            "payment_id": req.payment_id,
            "provider_ref": req.provider_ref,
            "amount": req.amount,
        }, provider_id
    )

    logger.info(f"Captured {req.payment_id} ({req.provider_ref})")
    return CaptureResponse(
        success=True, provider_ref=req.provider_ref, provider_id=provider_id
    )


@app.post("/providers/{provider_id}/refund", response_model=RefundResponse)
async def refund(provider_id: str, req: RefundRequest, background_tasks: BackgroundTasks):
    config = get_provider_config(provider_id)
    latency = rng.randint(config.latency_ms_min, config.latency_ms_max)
    await asyncio.sleep(latency / 1000.0)

    if rng.random() < config.error_rate:
        raise HTTPException(status_code=500, detail="Refund failed at provider")

    refund_ref = f"ref_{uuid.uuid4().hex[:12]}"

    background_tasks.add_task(
        send_webhook, "payment.refunded", {
            "payment_id": req.payment_id,
            "provider_ref": req.provider_ref,
            "refund_ref": refund_ref,
            "amount": req.amount,
        }, provider_id
    )

    logger.info(f"Refunded {req.payment_id} -> {refund_ref}")
    return RefundResponse(
        success=True, refund_ref=refund_ref, provider_id=provider_id
    )


@app.post("/providers/{provider_id}/inject-failure")
async def inject_failure(provider_id: str, req: InjectFailureRequest):
    current_config = get_provider_config(provider_id)
    updates = req.model_dump(exclude_none=True)
    new_config = current_config.model_copy(update=updates)

    state_path = _sim_state_path(provider_id)
    state = _read_sim_state(provider_id)
    state["failure_config"] = new_config.model_dump()
    FileStore.write_json(state_path, state)

    logger.info(f"Updated failure config for {provider_id}: {updates}")
    return {"message": f"Failure config updated for {provider_id}", "config": new_config.model_dump()}


@app.get("/providers/{provider_id}/state")
async def get_state(provider_id: str):
    state_path = _sim_state_path(provider_id)
    state = _read_sim_state(provider_id)
    config = get_provider_config(provider_id)
    state["failure_config"] = config.model_dump()
    return state


@app.get("/providers/{provider_id}/settlement")
async def generate_settlement(provider_id: str, date: Optional[str] = None):
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    # Read ledger to find captured/settled payments for this provider
    ledger_path = os.path.join(DATA_DIR, "ledger", "payments.jsonl")
    entries = FileStore.read_jsonl(ledger_path)

    settlement_rows = []
    for entry in entries:
        if entry.get("provider") == provider_id and entry.get("type") in (
            "payment.captured", "payment.settled"
        ):
            config = get_provider_config(provider_id)
            amount = entry.get("amount", 0)
            # Inject settlement mismatch
            if rng.random() < config.settlement_mismatch_rate:
                amount = amount - rng.randint(1, 500)

            settlement_rows.append({
                "payment_id": entry.get("ref", ""),
                "provider_ref": entry.get("metadata", {}).get("provider_ref", ""),
                "amount": amount,
                "currency": entry.get("currency", "USD"),
                "type": entry.get("type", ""),
                "status": "settled",
                "settled_at": entry.get("timestamp", datetime.utcnow().isoformat()),
            })

    csv_path = os.path.join(SETTLEMENT_DIR, f"settlement_{date}.csv")
    headers = ["payment_id", "provider_ref", "amount", "currency", "type", "status", "settled_at"]
    FileStore.write_csv(csv_path, headers, settlement_rows)

    return {
        "file": f"settlement_{date}.csv",
        "rows": len(settlement_rows),
        "provider": provider_id,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "provider-sim"}
