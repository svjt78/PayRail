"""Webhooks router - receives and validates provider webhooks."""

import os
import hmac
import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Header

from shared.file_store import FileStore
from shared.correlation import get_correlation_id, set_correlation_id
from services.ledger import LedgerService
from shared.models import LedgerEntry

logger = logging.getLogger("payrail.webhooks")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "whsec_payrail_demo_secret_key_2026")
PAYMENTS_STORE = os.path.join(DATA_DIR, "idempotency", "payments_store.json")
PROCESSED_WEBHOOKS = os.path.join(DATA_DIR, "outbox", "processed_webhooks.json")

ledger = LedgerService()


def validate_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/provider")
async def receive_webhook(
    request: Request,
    x_webhook_signature: str = Header("", alias="X-Webhook-Signature"),
    x_correlation_id: str = Header("", alias="X-Correlation-Id"),
):
    body = await request.body()

    # Validate HMAC signature
    if x_webhook_signature and not validate_signature(body, x_webhook_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_correlation_id:
        set_correlation_id(x_correlation_id)

    payload = json.loads(body)
    # Support both provider-style envelope and raw outbox payloads
    webhook_id = payload.get("id", payload.get("event_id", ""))
    event_type = payload.get("type", payload.get("event_type", ""))
    data = payload.get("data", payload.get("payload", payload))

    # Dedup: check if already processed
    processed = FileStore.read_json(PROCESSED_WEBHOOKS, default={})
    if webhook_id in processed:
        logger.info(f"Duplicate webhook {webhook_id}, skipping")
        return {"status": "duplicate", "webhook_id": webhook_id}

    # Process based on event type
    payment_id = data.get("payment_id")
    if payment_id:
        payments = FileStore.read_json(PAYMENTS_STORE, default={})
        payment = payments.get(payment_id)

        if payment:
            if event_type == "payment.authorized" and payment["state"] == "created":
                payment["state"] = "authorized"
                payment["provider_ref"] = data.get("provider_ref")
                payment["updated_at"] = datetime.utcnow().isoformat()
                payments[payment_id] = payment
                FileStore.write_json(PAYMENTS_STORE, payments)

            elif event_type == "payment.captured" and payment["state"] == "authorized":
                payment["state"] = "captured"
                payment["updated_at"] = datetime.utcnow().isoformat()
                payments[payment_id] = payment
                FileStore.write_json(PAYMENTS_STORE, payments)

            elif event_type == "payment.declined" and payment["state"] == "created":
                payment["state"] = "declined"
                payment["updated_at"] = datetime.utcnow().isoformat()
                payment.setdefault("metadata", {})["decline_reason"] = data.get("decline_reason")
                payments[payment_id] = payment
                FileStore.write_json(PAYMENTS_STORE, payments)

            elif event_type == "payment.refunded":
                logger.info(f"Webhook: payment {payment_id} refunded")

            # Write ledger entry for the webhook event
            entry = LedgerEntry(
                type=f"webhook.{event_type}",
                ref=payment_id,
                amount=data.get("amount", payment.get("amount", 0)),
                currency=payment.get("currency", "USD"),
                merchant_id=payment.get("merchant_id", ""),
                provider=payload.get("provider"),
                correlation_id=get_correlation_id(),
                metadata=data,
            )
            ledger.write_entry(entry)

    # Mark as processed
    processed[webhook_id] = {
        "processed_at": datetime.utcnow().isoformat(),
        "event_type": event_type,
    }
    FileStore.write_json(PROCESSED_WEBHOOKS, processed)

    logger.info(f"Processed webhook {webhook_id}: {event_type}")
    return {"status": "processed", "webhook_id": webhook_id}
