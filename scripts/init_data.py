"""Initialize data directory structure."""

import os

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

DIRS = [
    "ledger",
    "vault",
    "providers",
    "settlement",
    "metrics",
    "outbox",
    "idempotency",
    "reconciliation",
]


def init():
    for d in DIRS:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)
    print(f"Data directories initialized at {DATA_DIR}")


if __name__ == "__main__":
    init()
