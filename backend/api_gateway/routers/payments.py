"""Payment intents router - full lifecycle with idempotency, vault, and routing."""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse
import httpx

from shared.models import PaymentIntent, PaymentState, LedgerEntry
from shared.file_store import FileStore
from shared.correlation import get_correlation_id
from models.requests import CreatePaymentRequest, AuthorizePaymentRequest
from services.idempotency import IdempotencyService, IdempotencyConflictError
from services.ledger import LedgerService
from services.routing import RoutingEngine
from services.provider_client import ProviderClient, ProviderError, ProviderUnavailableError
from services.state_machine import validate_payment_transition, InvalidTransitionError

logger = logging.getLogger("payrail.payments")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
VAULT_SERVICE_URL = os.environ.get("VAULT_SERVICE_URL", "http://vault-service:8027")
PAYMENTS_STORE = os.path.join(DATA_DIR, "idempotency", "payments_store.json")

ledger = LedgerService()
idempotency = IdempotencyService()
routing = RoutingEngine()
provider_client = ProviderClient()


def _load_payments() -> dict:
    return FileStore.read_json(PAYMENTS_STORE, default={})


def _save_payment(payment: dict):
    payments = _load_payments()
    payments[payment["id"]] = payment
    FileStore.write_json(PAYMENTS_STORE, payments)


def _get_payment(payment_id: str) -> dict:
    payments = _load_payments()
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payments[payment_id]


@router.post("", status_code=201)
async def create_payment(
    req: CreatePaymentRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash(req.model_dump())
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Create payment intent
    payment = PaymentIntent(
        amount=req.amount,
        currency=req.currency,
        merchant_id=x_merchant_id,
        customer_email=req.customer_email,
        description=req.description,
        token=req.token,
        idempotency_key=idempotency_key,
        correlation_id=get_correlation_id(),
        metadata=req.metadata,
    )

    # Ledger-first: write event before anything else
    entry = LedgerEntry(
        type="payment.created",
        ref=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=payment.model_dump(),
    )
    ledger.write_entry(entry)

    # Persist payment state
    payment_data = payment.model_dump()
    payment_data["created_at"] = payment_data["created_at"].isoformat() if isinstance(payment_data["created_at"], datetime) else str(payment_data["created_at"])
    payment_data["updated_at"] = payment_data["updated_at"].isoformat() if isinstance(payment_data["updated_at"], datetime) else str(payment_data["updated_at"])
    _save_payment(payment_data)

    # Emit outbox event
    ledger.emit_outbox_event("payment.created", payment_data)

    # Store idempotency
    idempotency.store(idempotency_key, request_hash, payment_data, 201)

    logger.info(f"Created payment {payment.id} for merchant {x_merchant_id}")
    return payment_data


@router.get("")
async def list_payments(
    state: Optional[str] = Query(None),
    merchant_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    payments = _load_payments()
    items = list(payments.values())

    if state:
        items = [p for p in items if p.get("state") == state]
    if merchant_id:
        items = [p for p in items if p.get("merchant_id") == merchant_id]

    items.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    total = len(items)
    items = items[offset:offset + limit]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{payment_id}")
async def get_payment(payment_id: str):
    payment = _get_payment(payment_id)
    entries = ledger.get_entries_for_ref(payment_id)
    return {**payment, "ledger_entries": entries}


@router.post("/{payment_id}/authorize")
async def authorize_payment(
    payment_id: str,
    req: AuthorizePaymentRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "authorize",
        "payment_id": payment_id,
        **req.model_dump(),
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    payment = _get_payment(payment_id)

    # Validate state transition
    try:
        validate_payment_transition(payment["state"], PaymentState.AUTHORIZED.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Get card details - either tokenize PAN or use existing token
    token = req.token or payment.get("token")
    pan = None
    expiry = None

    if req.pan and req.expiry:
        # Tokenize the card via vault
        try:
            async with httpx.AsyncClient() as client:
                vault_resp = await client.post(
                    f"{VAULT_SERVICE_URL}/tokenize",
                    json={
                        "pan": req.pan,
                        "expiry": req.expiry,
                        "requester": "api-gateway",
                        "purpose": "authorization",
                    },
                    timeout=5.0,
                )
            if vault_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Vault tokenization failed")
            vault_data = vault_resp.json()
            token = vault_data["token"]
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Vault service unavailable")

        pan = req.pan
        expiry = req.expiry
    elif token:
        # Retrieve card from vault for provider
        try:
            async with httpx.AsyncClient() as client:
                vault_resp = await client.post(
                    f"{VAULT_SERVICE_URL}/charge-token",
                    json={"token": token, "requester": "api-gateway", "purpose": "authorization"},
                    timeout=5.0,
                )
            if vault_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Token not found in vault")
            card_data = vault_resp.json()
            pan = card_data["pan"]
            expiry = card_data["expiry"]
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Vault service unavailable")
    else:
        raise HTTPException(status_code=400, detail="Either pan+expiry or token required")

    # Select provider via routing engine
    provider_id = routing.select_provider(
        amount=payment["amount"],
        currency=payment["currency"],
    )

    # Call provider to authorize
    try:
        result = await provider_client.authorize(
            provider_id=provider_id,
            payment_id=payment_id,
            amount=payment["amount"],
            currency=payment["currency"],
            pan=pan,
            expiry=expiry,
            merchant_id=x_merchant_id,
        )
    except ProviderUnavailableError:
        # Try failover
        failover_id = os.environ.get("FAILOVER_PROVIDER", "providerB")
        if failover_id == provider_id:
            failover_id = os.environ.get("DEFAULT_PROVIDER", "providerA")
        try:
            result = await provider_client.authorize(
                provider_id=failover_id,
                payment_id=payment_id,
                amount=payment["amount"],
                currency=payment["currency"],
                pan=pan,
                expiry=expiry,
                merchant_id=x_merchant_id,
            )
            provider_id = failover_id
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"All providers failed: {e}")
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result.get("success"):
        new_state = PaymentState.AUTHORIZED.value
    else:
        new_state = PaymentState.DECLINED.value

    # Update payment
    now = datetime.utcnow().isoformat()
    payment["state"] = new_state
    payment["provider"] = provider_id
    payment["token"] = token
    payment["provider_ref"] = result.get("provider_ref")
    payment["updated_at"] = now

    if not result.get("success"):
        payment["metadata"]["decline_reason"] = result.get("decline_reason")

    _save_payment(payment)

    # Write ledger entry
    event_type = "payment.authorized" if result.get("success") else "payment.declined"
    entry = LedgerEntry(
        type=event_type,
        ref=payment_id,
        amount=payment["amount"],
        currency=payment["currency"],
        merchant_id=x_merchant_id,
        provider=provider_id,
        correlation_id=get_correlation_id(),
        metadata=payment,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event(event_type, payment)

    logger.info(f"Payment {payment_id} -> {new_state} via {provider_id}")

    idempotency.store(idempotency_key, request_hash, payment, 200)
    return payment


@router.post("/{payment_id}/capture")
async def capture_payment(
    payment_id: str,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "capture",
        "payment_id": payment_id,
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    payment = _get_payment(payment_id)

    try:
        validate_payment_transition(payment["state"], PaymentState.CAPTURED.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    provider_id = payment.get("provider")
    provider_ref = payment.get("provider_ref")
    if not provider_id or not provider_ref:
        raise HTTPException(status_code=400, detail="Payment not yet authorized with a provider")

    try:
        result = await provider_client.capture(
            provider_id=provider_id,
            payment_id=payment_id,
            provider_ref=provider_ref,
            amount=payment["amount"],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Capture failed: {e}")

    now = datetime.utcnow().isoformat()
    payment["state"] = PaymentState.CAPTURED.value
    payment["updated_at"] = now
    _save_payment(payment)

    entry = LedgerEntry(
        type="payment.captured",
        ref=payment_id,
        amount=payment["amount"],
        currency=payment["currency"],
        merchant_id=x_merchant_id,
        provider=provider_id,
        correlation_id=get_correlation_id(),
        metadata=payment,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event("payment.captured", payment)

    logger.info(f"Captured payment {payment_id}")

    idempotency.store(idempotency_key, request_hash, payment, 200)
    return payment


@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: str,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "cancel",
        "payment_id": payment_id,
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    payment = _get_payment(payment_id)

    try:
        validate_payment_transition(payment["state"], PaymentState.REVERSED.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    now = datetime.utcnow().isoformat()
    payment["state"] = PaymentState.REVERSED.value
    payment["updated_at"] = now
    _save_payment(payment)

    entry = LedgerEntry(
        type="payment.reversed",
        ref=payment_id,
        amount=payment["amount"],
        currency=payment["currency"],
        merchant_id=x_merchant_id,
        provider=payment.get("provider"),
        correlation_id=get_correlation_id(),
        metadata=payment,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event("payment.reversed", payment)

    logger.info(f"Reversed payment {payment_id}")

    idempotency.store(idempotency_key, request_hash, payment, 200)
    return payment
