"""Outbox dispatcher - reads events and sends webhooks with retry/DLQ."""

import os
import json
import hmac
import hashlib
import logging
import asyncio
from datetime import datetime

import httpx

from shared.file_store import FileStore

logger = logging.getLogger("ledger-jobs.outbox")

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUTBOX_PATH = os.path.join(DATA_DIR, "outbox", "events.jsonl")
PROCESSED_PATH = os.path.join(DATA_DIR, "outbox", "processed_events.json")
DLQ_PATH = os.path.join(DATA_DIR, "outbox", "dlq.jsonl")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "whsec_payrail_demo_secret_key_2026")
WEBHOOK_CALLBACK_URL = os.environ.get("WEBHOOK_CALLBACK_URL", "http://api-gateway:8026/webhooks/provider")

MAX_RETRIES = 3
RETRY_BACKOFF = [1, 3, 10]  # seconds


def sign_payload(payload: str) -> str:
    sig = hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"sha256={sig}"


class OutboxDispatcher:

    async def dispatch_event(self, event: dict) -> bool:
        payload_obj = {
            "id": event.get("event_id", f"oevt_{datetime.utcnow().timestamp()}"),
            "type": event.get("type", ""),
            "provider": event.get("payload", {}).get("provider"),
            "data": event.get("payload", {}),
            "created_at": event.get("created_at", datetime.utcnow().isoformat()),
        }
        payload = json.dumps(payload_obj, default=str)
        signature = sign_payload(payload)

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        WEBHOOK_CALLBACK_URL,
                        content=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": signature,
                            "X-Correlation-Id": event.get("correlation_id", ""),
                        },
                        timeout=10.0,
                    )
                if resp.status_code < 400:
                    return True
                logger.warning(f"Webhook returned {resp.status_code}, attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Webhook delivery failed (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF[attempt])

        return False

    async def run_loop(self, interval: int = 5):
        logger.info(f"Outbox dispatcher started (interval={interval}s)")
        while True:
            try:
                await self.process_pending()
            except Exception as e:
                logger.error(f"Outbox dispatcher error: {e}")
            await asyncio.sleep(interval)

    async def process_pending(self):
        events = FileStore.read_jsonl(OUTBOX_PATH)
        if not events:
            return

        processed = FileStore.read_json(PROCESSED_PATH, default={})
        pending = [e for e in events if e.get("event_id") not in processed]

        if not pending:
            return

        logger.info(f"Processing {len(pending)} outbox events")

        for event in pending:
            event_id = event.get("event_id", "")
            success = await self.dispatch_event(event)

            if success:
                processed[event_id] = {
                    "processed_at": __import__("datetime").datetime.utcnow().isoformat(),
                    "status": "delivered",
                }
                logger.info(f"Delivered outbox event {event_id}")
            else:
                # Move to DLQ
                FileStore.append_jsonl(DLQ_PATH, {
                    **event,
                    "dlq_reason": "max_retries_exceeded",
                    "dlq_at": __import__("datetime").datetime.utcnow().isoformat(),
                })
                processed[event_id] = {
                    "processed_at": __import__("datetime").datetime.utcnow().isoformat(),
                    "status": "dlq",
                }
                logger.warning(f"Event {event_id} moved to DLQ")

        FileStore.write_json(PROCESSED_PATH, processed)
