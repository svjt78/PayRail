"""Refunds router - maker-checker workflow with approval chain."""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse

from shared.models import Refund, RefundState, LedgerEntry
from shared.file_store import FileStore
from shared.correlation import get_correlation_id
from models.requests import CreateRefundRequest
from services.ledger import LedgerService
from services.provider_client import ProviderClient
from services.state_machine import validate_refund_transition, InvalidTransitionError
from services.idempotency import IdempotencyService, IdempotencyConflictError

logger = logging.getLogger("payrail.refunds")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
REFUNDS_STORE = os.path.join(DATA_DIR, "idempotency", "refunds_store.json")
PAYMENTS_STORE = os.path.join(DATA_DIR, "idempotency", "payments_store.json")

ledger = LedgerService()
provider_client = ProviderClient()
idempotency = IdempotencyService()


def _load_refunds() -> dict:
    return FileStore.read_json(REFUNDS_STORE, default={})


def _save_refund(refund: dict):
    refunds = _load_refunds()
    refunds[refund["id"]] = refund
    FileStore.write_json(REFUNDS_STORE, refunds)


def _get_refund(refund_id: str) -> dict:
    refunds = _load_refunds()
    if refund_id not in refunds:
        raise HTTPException(status_code=404, detail=f"Refund {refund_id} not found")
    return refunds[refund_id]


@router.post("", status_code=201)
async def create_refund(
    req: CreateRefundRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "create_refund",
        **req.model_dump(),
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Verify payment exists and is captured/settled
    payments = FileStore.read_json(PAYMENTS_STORE, default={})
    payment = payments.get(req.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {req.payment_id} not found")
    if payment["state"] not in ("captured", "settled"):
        raise HTTPException(status_code=409, detail=f"Payment must be captured or settled to refund")
    if req.amount > payment["amount"]:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    refund = Refund(
        payment_id=req.payment_id,
        amount=req.amount,
        currency=payment.get("currency", "USD"),
        reason=req.reason,
        requested_by=x_merchant_id,
        merchant_id=x_merchant_id,
        state=RefundState.PENDING_APPROVAL,
        correlation_id=get_correlation_id(),
    )

    refund_data = refund.model_dump()
    refund_data["created_at"] = refund_data["created_at"].isoformat() if isinstance(refund_data["created_at"], datetime) else str(refund_data["created_at"])
    refund_data["updated_at"] = refund_data["updated_at"].isoformat() if isinstance(refund_data["updated_at"], datetime) else str(refund_data["updated_at"])

    # Ledger-first
    entry = LedgerEntry(
        type="refund.created",
        ref=refund.id,
        amount=refund.amount,
        currency=refund.currency,
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=refund_data,
    )
    ledger.write_entry(entry)
    _save_refund(refund_data)
    ledger.emit_outbox_event("refund.created", refund_data)

    logger.info(f"Refund {refund.id} created for payment {req.payment_id} (pending approval)")

    idempotency.store(idempotency_key, request_hash, refund_data, 201)
    return refund_data


@router.get("")
async def list_refunds(
    state: Optional[str] = Query(None),
    payment_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    refunds = _load_refunds()
    items = list(refunds.values())

    if state:
        items = [r for r in items if r.get("state") == state]
    if payment_id:
        items = [r for r in items if r.get("payment_id") == payment_id]

    items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    total = len(items)
    items = items[offset:offset + limit]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{refund_id}")
async def get_refund(refund_id: str):
    refund = _get_refund(refund_id)
    entries = ledger.get_entries_for_ref(refund_id)
    return {**refund, "ledger_entries": entries}


@router.post("/{refund_id}/approve")
async def approve_refund(
    refund_id: str,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    x_role: str = Header("operator", alias="X-Role"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "approve_refund",
        "refund_id": refund_id,
        "merchant_id": x_merchant_id,
        "role": x_role,
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    refund = _get_refund(refund_id)

    # Maker-checker: approver must be different from requester
    if refund.get("requested_by") == x_merchant_id and x_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Approver must be different from requester (maker-checker)",
        )

    try:
        validate_refund_transition(refund["state"], RefundState.APPROVED.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    now = datetime.utcnow().isoformat()
    refund["state"] = RefundState.APPROVED.value
    refund["approved_by"] = x_merchant_id
    refund["updated_at"] = now

    # Process the refund via provider
    payments = FileStore.read_json(PAYMENTS_STORE, default={})
    payment = payments.get(refund["payment_id"])

    if payment and payment.get("provider") and payment.get("provider_ref"):
        try:
            result = await provider_client.refund(
                provider_id=payment["provider"],
                payment_id=refund["payment_id"],
                provider_ref=payment["provider_ref"],
                amount=refund["amount"],
            )
            if result.get("success"):
                refund["state"] = RefundState.SUCCEEDED.value
            else:
                refund["state"] = RefundState.FAILED.value
        except Exception as e:
            logger.error(f"Provider refund failed: {e}")
            refund["state"] = RefundState.FAILED.value
    else:
        refund["state"] = RefundState.SUCCEEDED.value

    refund["updated_at"] = datetime.utcnow().isoformat()
    _save_refund(refund)

    entry = LedgerEntry(
        type=f"refund.{refund['state']}",
        ref=refund_id,
        amount=refund["amount"],
        currency=refund.get("currency", "USD"),
        merchant_id=x_merchant_id,
        provider=payment.get("provider") if payment else None,
        correlation_id=get_correlation_id(),
        metadata=refund,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event(f"refund.{refund['state']}", refund)

    logger.info(f"Refund {refund_id} -> {refund['state']}")

    idempotency.store(idempotency_key, request_hash, refund, 200)
    return refund


@router.post("/{refund_id}/reject")
async def reject_refund(
    refund_id: str,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "reject_refund",
        "refund_id": refund_id,
        "merchant_id": x_merchant_id,
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    refund = _get_refund(refund_id)

    try:
        validate_refund_transition(refund["state"], RefundState.FAILED.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    now = datetime.utcnow().isoformat()
    refund["state"] = RefundState.FAILED.value
    refund["updated_at"] = now
    refund["metadata"] = refund.get("metadata", {})
    refund["metadata"]["rejection_reason"] = "Rejected by approver"
    _save_refund(refund)

    entry = LedgerEntry(
        type="refund.failed",
        ref=refund_id,
        amount=refund["amount"],
        currency=refund.get("currency", "USD"),
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=refund,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event("refund.rejected", refund)

    logger.info(f"Refund {refund_id} rejected")

    idempotency.store(idempotency_key, request_hash, refund, 200)
    return refund
