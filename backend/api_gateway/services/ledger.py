"""Ledger service - immutable append-only event store and outbox emitter."""

import os
from datetime import datetime
from shared.file_store import FileStore
from shared.models import LedgerEntry, OutboxEvent
from shared.correlation import get_correlation_id

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")


class LedgerService:

    def __init__(self):
        self.payments_path = os.path.join(DATA_DIR, "ledger", "payments.jsonl")
        self.refunds_path = os.path.join(DATA_DIR, "ledger", "refunds.jsonl")
        self.disputes_path = os.path.join(DATA_DIR, "ledger", "disputes.jsonl")
        self.outbox_path = os.path.join(DATA_DIR, "outbox", "events.jsonl")

    def _path_for_type(self, event_type: str) -> str:
        if event_type.startswith("refund."):
            return self.refunds_path
        if event_type.startswith("dispute."):
            return self.disputes_path
        return self.payments_path

    def write_entry(self, entry: LedgerEntry) -> None:
        path = self._path_for_type(entry.type)
        FileStore.append_jsonl(path, entry.model_dump())

    def get_entries_for_ref(self, ref_id: str) -> list[dict]:
        all_entries = []
        for path in [self.payments_path, self.refunds_path, self.disputes_path]:
            entries = FileStore.read_jsonl(path)
            all_entries.extend([e for e in entries if e.get("ref") == ref_id])
        return sorted(all_entries, key=lambda e: e.get("timestamp", ""))

    def get_current_state(self, ref_id: str, entity_type: str = "payment") -> dict | None:
        if entity_type == "payment":
            path = self.payments_path
        elif entity_type == "refund":
            path = self.refunds_path
        else:
            path = self.disputes_path

        entries = FileStore.read_jsonl(path)
        ref_entries = [e for e in entries if e.get("ref") == ref_id]
        if not ref_entries:
            return None

        # The latest entry's metadata contains the current state
        latest = ref_entries[-1]
        return latest.get("metadata", {})

    def get_all_payments(self) -> list[dict]:
        entries = FileStore.read_jsonl(self.payments_path)
        # Group by ref, get latest state for each
        payments = {}
        for entry in entries:
            ref = entry.get("ref")
            if ref:
                if ref not in payments:
                    payments[ref] = entry.get("metadata", {})
                else:
                    payments[ref].update(entry.get("metadata", {}))
                # Track latest state
                payments[ref]["_latest_type"] = entry.get("type", "")
                payments[ref]["_latest_timestamp"] = entry.get("timestamp", "")
        return list(payments.values())

    def emit_outbox_event(self, event_type: str, payload: dict) -> None:
        event = OutboxEvent(
            type=event_type,
            payload=payload,
            correlation_id=get_correlation_id(),
        )
        FileStore.append_jsonl(self.outbox_path, event.model_dump())

    def get_all_entries(self, entity_type: str = "payment", limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        if entity_type == "payment":
            path = self.payments_path
        elif entity_type == "refund":
            path = self.refunds_path
        else:
            path = self.disputes_path

        entries = FileStore.read_jsonl(path)
        total = len(entries)
        entries.reverse()  # newest first
        return entries[offset:offset + limit], total
