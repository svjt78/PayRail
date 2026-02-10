"""Settlement generator - creates daily settlement CSV from ledger."""

import os
import logging
import uuid
from datetime import datetime

from shared.file_store import FileStore

logger = logging.getLogger("ledger-jobs.settlement")

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
LEDGER_PATH = os.path.join(DATA_DIR, "ledger", "payments.jsonl")
SETTLEMENT_DIR = os.path.join(DATA_DIR, "settlement")
PAYMENTS_STORE = os.path.join(DATA_DIR, "idempotency", "payments_store.json")
OUTBOX_PATH = os.path.join(DATA_DIR, "outbox", "events.jsonl")

CSV_HEADERS = [
    "payment_id", "provider_ref", "amount", "currency",
    "type", "status", "settled_at",
]


class SettlementGenerator:

    def generate(self, date: str = None):
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        entries = FileStore.read_jsonl(LEDGER_PATH)
        payments = FileStore.read_json(PAYMENTS_STORE, default={})
        settled_refs = {e.get("ref") for e in entries if e.get("type") == "payment.settled"}

        # Filter captured/settled entries for the target date (for CSV)
        rows = []
        seen_payments = set()

        # Promote captured payments to settled regardless of capture date
        for entry in entries:
            if entry.get("type") not in ("payment.captured", "payment.settled"):
                continue
            payment_id = entry.get("ref", "")
            payment = payments.get(payment_id)
            if not payment:
                continue
            if payment.get("state") == "captured" and payment_id not in settled_refs:
                payment["state"] = "settled"
                payment["updated_at"] = datetime.utcnow().isoformat()
                payments[payment_id] = payment

                settled_entry = {
                    "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                    "type": "payment.settled",
                    "ref": payment_id,
                    "amount": entry.get("amount", 0),
                    "currency": entry.get("currency", "USD"),
                    "merchant_id": payment.get("merchant_id", ""),
                    "provider": entry.get("provider"),
                    "correlation_id": "corr_settlement_job",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": payment,
                }
                FileStore.append_jsonl(LEDGER_PATH, settled_entry)

                outbox_event = {
                    "event_id": f"oevt_{uuid.uuid4().hex[:12]}",
                    "type": "payment.settled",
                    "payload": payment,
                    "correlation_id": "corr_settlement_job",
                    "created_at": datetime.utcnow().isoformat(),
                }
                FileStore.append_jsonl(OUTBOX_PATH, outbox_event)

        for entry in entries:
            if entry.get("type") not in ("payment.captured", "payment.settled"):
                continue

            timestamp = entry.get("timestamp", "")
            if isinstance(timestamp, str) and timestamp.startswith(date):
                payment_id = entry.get("ref", "")
                if payment_id in seen_payments:
                    continue
                seen_payments.add(payment_id)

                metadata = entry.get("metadata", {})
                rows.append({
                    "payment_id": payment_id,
                    "provider_ref": metadata.get("provider_ref", ""),
                    "amount": entry.get("amount", 0),
                    "currency": entry.get("currency", "USD"),
                    "type": entry.get("type", ""),
                    "status": "settled",
                    "settled_at": timestamp,
                })


        if rows:
            csv_path = os.path.join(SETTLEMENT_DIR, f"settlement_{date}.csv")
            FileStore.write_csv(csv_path, CSV_HEADERS, rows)
            logger.info(f"Generated settlement for {date}: {len(rows)} rows")
        else:
            logger.info(f"No settled payments for {date}")

        if payments:
            FileStore.write_json(PAYMENTS_STORE, payments)

        return rows

    async def run_loop(self, interval: int = 3600):
        import asyncio
        logger.info(f"Settlement generator started (interval={interval}s)")
        while True:
            try:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                self.generate(today)
            except Exception as e:
                logger.error(f"Settlement generator error: {e}")
            await asyncio.sleep(interval)
