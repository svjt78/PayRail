"""Reconciliation job - compares ledger against settlement CSV."""

import os
import logging
from datetime import datetime
from collections import defaultdict

from shared.file_store import FileStore

logger = logging.getLogger("ledger-jobs.reconciliation")

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
LEDGER_PATH = os.path.join(DATA_DIR, "ledger", "payments.jsonl")
SETTLEMENT_DIR = os.path.join(DATA_DIR, "settlement")
RECON_DIR = os.path.join(DATA_DIR, "reconciliation")


class ReconciliationJob:

    def reconcile(self, date: str = None):
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        os.makedirs(RECON_DIR, exist_ok=True)

        # Load ledger totals for captured/settled payments
        entries = FileStore.read_jsonl(LEDGER_PATH)
        ledger_amounts = {}
        for entry in entries:
            if entry.get("type") in ("payment.captured", "payment.settled"):
                ref = entry.get("ref", "")
                ledger_amounts[ref] = int(entry.get("amount", 0))

        # Load settlement CSV
        csv_path = os.path.join(SETTLEMENT_DIR, f"settlement_{date}.csv")
        settlement_rows = FileStore.read_csv(csv_path)
        settlement_amounts = {}
        for row in settlement_rows:
            pid = row.get("payment_id", "")
            settlement_amounts[pid] = int(row.get("amount", 0))

        # Compare
        all_ids = set(ledger_amounts.keys()) | set(settlement_amounts.keys())
        matched = 0
        mismatched = 0
        missing_from_settlement = 0
        missing_from_ledger = 0
        mismatches = []

        for pid in all_ids:
            ledger_amt = ledger_amounts.get(pid)
            settle_amt = settlement_amounts.get(pid)

            if ledger_amt is None:
                missing_from_ledger += 1
                mismatches.append({
                    "payment_id": pid,
                    "ledger_amount": None,
                    "settlement_amount": settle_amt,
                    "issue": "missing_from_ledger",
                })
            elif settle_amt is None:
                missing_from_settlement += 1
                mismatches.append({
                    "payment_id": pid,
                    "ledger_amount": ledger_amt,
                    "settlement_amount": None,
                    "issue": "missing_from_settlement",
                })
            elif ledger_amt != settle_amt:
                mismatched += 1
                mismatches.append({
                    "payment_id": pid,
                    "ledger_amount": ledger_amt,
                    "settlement_amount": settle_amt,
                    "diff": ledger_amt - settle_amt,
                    "issue": "amount_mismatch",
                })
            else:
                matched += 1

        total_ledger = sum(ledger_amounts.values())
        total_settlement = sum(settlement_amounts.values())

        status = "clean" if not mismatches else "mismatches_found"
        report = {
            "date": date,
            "status": status,
            "total_ledger": total_ledger,
            "total_settlement": total_settlement,
            "diff": total_ledger - total_settlement,
            "matched": matched,
            "mismatched": mismatched,
            "missing_from_settlement": missing_from_settlement,
            "missing_from_ledger": missing_from_ledger,
            "mismatches": mismatches,
            "generated_at": datetime.utcnow().isoformat(),
        }

        report_path = os.path.join(RECON_DIR, f"reconciliation_report_{date}.json")
        FileStore.write_json(report_path, report)

        logger.info(
            f"Reconciliation {date}: {matched} matched, "
            f"{mismatched} mismatched, {missing_from_settlement} missing from settlement, "
            f"{missing_from_ledger} missing from ledger"
        )
        return report

    async def run_loop(self, interval: int = 3600):
        import asyncio
        logger.info(f"Reconciliation job started (interval={interval}s)")
        while True:
            try:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                self.reconcile(today)
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")
            await asyncio.sleep(interval)
