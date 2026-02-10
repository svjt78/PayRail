"""Ledger Jobs - Background service running outbox, settlement, and reconciliation."""

import os
import sys
import asyncio
import logging

sys.path.insert(0, "/app/shared")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("ledger-jobs")

# Initialize data dirs
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
for d in ["ledger", "outbox", "settlement", "reconciliation", "metrics"]:
    os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)

from outbox_dispatcher import OutboxDispatcher
from settlement_generator import SettlementGenerator
from reconciliation import ReconciliationJob


async def main():
    logger.info("Ledger Jobs service starting...")

    dispatcher = OutboxDispatcher()
    settlement = SettlementGenerator()
    reconciliation = ReconciliationJob()

    # Run all background loops concurrently
    await asyncio.gather(
        dispatcher.run_loop(interval=5),
        settlement.run_loop(interval=10),
        reconciliation.run_loop(interval=3600),
    )


if __name__ == "__main__":
    asyncio.run(main())
