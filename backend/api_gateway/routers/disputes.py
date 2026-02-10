"""Disputes router - open, review, and resolve disputes."""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse

from shared.models import Dispute, DisputeState, LedgerEntry
from shared.file_store import FileStore
from shared.correlation import get_correlation_id
from models.requests import CreateDisputeRequest, SubmitEvidenceRequest, ResolveDisputeRequest
from services.ledger import LedgerService
from services.state_machine import validate_dispute_transition, InvalidTransitionError
from services.idempotency import IdempotencyService, IdempotencyConflictError

logger = logging.getLogger("payrail.disputes")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
DISPUTES_STORE = os.path.join(DATA_DIR, "idempotency", "disputes_store.json")
PAYMENTS_STORE = os.path.join(DATA_DIR, "idempotency", "payments_store.json")

ledger = LedgerService()
idempotency = IdempotencyService()


def _load_disputes() -> dict:
    return FileStore.read_json(DISPUTES_STORE, default={})


def _save_dispute(dispute: dict):
    disputes = _load_disputes()
    disputes[dispute["id"]] = dispute
    FileStore.write_json(DISPUTES_STORE, disputes)


def _get_dispute(dispute_id: str) -> dict:
    disputes = _load_disputes()
    if dispute_id not in disputes:
        raise HTTPException(status_code=404, detail=f"Dispute {dispute_id} not found")
    return disputes[dispute_id]


@router.post("", status_code=201)
async def create_dispute(
    req: CreateDisputeRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "create_dispute",
        **req.model_dump(),
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Verify payment exists
    payments = FileStore.read_json(PAYMENTS_STORE, default={})
    payment = payments.get(req.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {req.payment_id} not found")

    dispute = Dispute(
        payment_id=req.payment_id,
        amount=req.amount,
        reason=req.reason,
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
    )

    dispute_data = dispute.model_dump()
    dispute_data["created_at"] = dispute_data["created_at"].isoformat() if isinstance(dispute_data["created_at"], datetime) else str(dispute_data["created_at"])
    dispute_data["updated_at"] = dispute_data["updated_at"].isoformat() if isinstance(dispute_data["updated_at"], datetime) else str(dispute_data["updated_at"])

    # Ledger-first
    entry = LedgerEntry(
        type="dispute.opened",
        ref=dispute.id,
        amount=dispute.amount,
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=dispute_data,
    )
    ledger.write_entry(entry)
    _save_dispute(dispute_data)
    ledger.emit_outbox_event("dispute.opened", dispute_data)

    # Mark payment as chargeback if captured
    if payment["state"] in ("captured", "settled"):
        payment["state"] = "chargeback"
        payment["updated_at"] = datetime.utcnow().isoformat()
        payments[req.payment_id] = payment
        FileStore.write_json(PAYMENTS_STORE, payments)

    logger.info(f"Dispute {dispute.id} opened for payment {req.payment_id}")

    idempotency.store(idempotency_key, request_hash, dispute_data, 201)
    return dispute_data


@router.get("")
async def list_disputes(
    state: Optional[str] = Query(None),
    payment_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    disputes = _load_disputes()
    items = list(disputes.values())

    if state:
        items = [d for d in items if d.get("state") == state]
    if payment_id:
        items = [d for d in items if d.get("payment_id") == payment_id]

    items.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    total = len(items)
    items = items[offset:offset + limit]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{dispute_id}")
async def get_dispute(dispute_id: str):
    dispute = _get_dispute(dispute_id)
    entries = ledger.get_entries_for_ref(dispute_id)
    return {**dispute, "ledger_entries": entries}


@router.post("/{dispute_id}/submit-evidence")
async def submit_evidence(
    dispute_id: str,
    req: SubmitEvidenceRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "submit_evidence",
        "dispute_id": dispute_id,
        **req.model_dump(),
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    dispute = _get_dispute(dispute_id)

    try:
        validate_dispute_transition(dispute["state"], DisputeState.UNDER_REVIEW.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    now = datetime.utcnow().isoformat()
    dispute["state"] = DisputeState.UNDER_REVIEW.value
    dispute["evidence"] = req.evidence
    dispute["updated_at"] = now
    _save_dispute(dispute)

    entry = LedgerEntry(
        type="dispute.under_review",
        ref=dispute_id,
        amount=dispute["amount"],
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=dispute,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event("dispute.under_review", dispute)

    logger.info(f"Evidence submitted for dispute {dispute_id}")

    idempotency.store(idempotency_key, request_hash, dispute, 200)
    return dispute


@router.post("/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    req: ResolveDisputeRequest,
    x_merchant_id: str = Header(..., alias="X-Merchant-Id"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check idempotency
    request_hash = idempotency.compute_hash({
        "action": "resolve_dispute",
        "dispute_id": dispute_id,
        **req.model_dump(),
    })
    try:
        cached = idempotency.check(idempotency_key, request_hash)
        if cached:
            return JSONResponse(cached.response, status_code=cached.status_code)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=422, detail=str(e))

    dispute = _get_dispute(dispute_id)

    if req.outcome not in ("won", "lost"):
        raise HTTPException(status_code=400, detail="Outcome must be 'won' or 'lost'")

    target = DisputeState.WON if req.outcome == "won" else DisputeState.LOST
    try:
        validate_dispute_transition(dispute["state"], target.value)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    now = datetime.utcnow().isoformat()
    dispute["state"] = target.value
    dispute["updated_at"] = now
    _save_dispute(dispute)

    entry = LedgerEntry(
        type=f"dispute.{target.value}",
        ref=dispute_id,
        amount=dispute["amount"],
        merchant_id=x_merchant_id,
        correlation_id=get_correlation_id(),
        metadata=dispute,
    )
    ledger.write_entry(entry)
    ledger.emit_outbox_event(f"dispute.{target.value}", dispute)

    logger.info(f"Dispute {dispute_id} resolved: {target.value}")

    idempotency.store(idempotency_key, request_hash, dispute, 200)
    return dispute
