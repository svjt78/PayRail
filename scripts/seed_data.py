"""
Deterministic synthetic data generator for PayRail.
Generates Luhn-valid PANs, customers, payments, refunds, disputes,
settlement CSVs, vault tokens, and provider states.
"""

import json
import os
import random
import csv
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, "/app/shared")

SEED = int(os.environ.get("SEED", 42))
DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
rng = random.Random(SEED)

# === Helpers ===

def ensure_dirs():
    for d in ["ledger", "vault", "providers", "settlement", "metrics",
              "outbox", "idempotency", "reconciliation"]:
        os.makedirs(os.path.join(DATA_DIR, d), exist_ok=True)


def generate_pan(prefix: str = "4111", length: int = 16) -> str:
    """Generate a Luhn-valid PAN."""
    num = list(prefix)
    while len(num) < length - 1:
        num.append(str(rng.randint(0, 9)))
    # Luhn check digit
    digits = [int(d) for d in num]
    odd_sum = sum(digits[-1::-2])
    even_sum = sum(sum(divmod(d * 2, 10)) for d in digits[-2::-2])
    check = (10 - ((odd_sum + even_sum) % 10)) % 10
    num.append(str(check))
    return "".join(num)


# === Data Tables ===

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank",
               "Grace", "Henry", "Iris", "Jack", "Karen", "Leo",
               "Maria", "Nathan", "Olivia", "Peter", "Quinn", "Rosa",
               "Sam", "Tina"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones",
              "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

COUNTRIES = ["US", "GB", "DE", "FR", "JP", "AU", "CA"]
CURRENCY_MAP = {"US": "USD", "GB": "GBP", "DE": "EUR", "FR": "EUR",
                "JP": "JPY", "AU": "AUD", "CA": "CAD"}

BIN_TABLE = {
    "4111": {"brand": "visa", "type": "credit"},
    "4242": {"brand": "visa", "type": "debit"},
    "5500": {"brand": "mastercard", "type": "credit"},
    "5105": {"brand": "mastercard", "type": "debit"},
    "3782": {"brand": "amex", "type": "credit"},
}

AMOUNTS = [499, 999, 1499, 2500, 3500, 5000, 7500, 10000, 15000, 25000, 50000]
DESCRIPTIONS = [
    "Monthly subscription", "Annual plan", "One-time purchase",
    "Premium upgrade", "Enterprise license", "Consultation fee",
    "Hardware purchase", "Service fee", "Donation", "Event ticket",
]

DECLINE_REASONS = ["insufficient_funds", "card_declined", "expired_card", "processing_error"]
DISPUTE_REASONS = [
    "Unauthorized transaction", "Product not received",
    "Product not as described", "Duplicate charge",
    "Subscription cancellation not processed",
]


# === Generators ===

def generate_customers(n: int = 20) -> list:
    customers = []
    for i in range(n):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        country = rng.choice(COUNTRIES)
        customers.append({
            "id": f"cust_{i:04d}",
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@example.com",
            "country": country,
            "currency": CURRENCY_MAP.get(country, "USD"),
            "ip": f"{rng.randint(1,255)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
        })
    return customers


def generate_cards(customers: list) -> list:
    cards = []
    for cust in customers:
        for _ in range(rng.randint(1, 2)):
            prefix = rng.choice(list(BIN_TABLE.keys()))
            pan = generate_pan(prefix)
            cards.append({
                "customer_id": cust["id"],
                "pan": pan,
                "expiry": f"{rng.randint(1,12):02d}/{rng.randint(26,30)}",
                "cvv": f"{rng.randint(100, 999)}",
                "brand": BIN_TABLE[prefix]["brand"],
                "last_four": pan[-4:],
            })
    return cards


def generate_token(pan: str) -> str:
    return f"tok_{hashlib.sha256(pan.encode()).hexdigest()[:24]}"


def seed_all():
    ensure_dirs()
    print("Generating synthetic data with seed:", SEED)

    customers = generate_customers(20)
    cards = generate_cards(customers)

    # === Vault: Tokenize all cards ===
    tokens = {}
    encrypted_cards = {}
    access_log = []

    for card in cards:
        token = generate_token(card["pan"])
        # Fake encryption (in real app, VaultCrypto handles this)
        encrypted = f"enc_{card['pan'][:6]}...{card['pan'][-4:]}"
        tokens[token] = encrypted
        encrypted_cards[token] = {
            "encrypted_pan": encrypted,
            "bin": card["pan"][:6],
            "last_four": card["last_four"],
            "expiry": card["expiry"],
            "card_brand": card["brand"],
            "cardholder_name": None,
            "created_at": datetime(2026, 2, 1).isoformat(),
        }
        access_log.append({
            "timestamp": datetime(2026, 2, 1).isoformat(),
            "action": "tokenize",
            "token": token,
            "requester": "seed-script",
            "purpose": "seed-data",
            "correlation_id": f"corr_seed_{card['customer_id']}",
        })

    _write_json("vault/tokens.json", tokens)
    _write_json("vault/encrypted_cards.json", encrypted_cards)
    _write_jsonl("vault/access_log.jsonl", access_log)
    print(f"  Vault: {len(tokens)} tokens")

    # === Generate Payments ===
    payments = {}
    ledger_entries = []
    idempotency_keys = {}
    base_time = datetime(2026, 2, 1, 8, 0, 0)

    states_dist = ["authorized", "authorized", "captured", "captured", "captured",
                   "settled", "settled", "settled", "declined", "created"]

    for i in range(50):
        cust = rng.choice(customers)
        cust_cards = [c for c in cards if c["customer_id"] == cust["id"]]
        card = rng.choice(cust_cards) if cust_cards else rng.choice(cards)
        token = generate_token(card["pan"])

        state = rng.choice(states_dist)
        provider = rng.choice(["providerA", "providerB"])
        amount = rng.choice(AMOUNTS)
        created = base_time + timedelta(hours=rng.randint(0, 200), minutes=rng.randint(0, 59))

        ref_prefix = "ch_" if provider == "providerA" else "PSP_"
        provider_ref = f"{ref_prefix}{uuid.uuid4().hex[:12]}" if state != "created" else None

        pid = f"pi_{i:06d}"
        idem_key = f"idem_{i:06d}"

        payment = {
            "id": pid,
            "amount": amount,
            "currency": cust["currency"],
            "state": state,
            "merchant_id": "m_001",
            "customer_email": cust["email"],
            "description": rng.choice(DESCRIPTIONS),
            "provider": provider if state != "created" else None,
            "token": token,
            "provider_ref": provider_ref,
            "idempotency_key": idem_key,
            "correlation_id": f"corr_{i:06d}",
            "created_at": created.isoformat(),
            "updated_at": created.isoformat(),
            "metadata": {},
        }

        if state == "declined":
            payment["metadata"]["decline_reason"] = rng.choice(DECLINE_REASONS)

        payments[pid] = payment

        # Idempotency key
        body_hash = hashlib.sha256(json.dumps({
            "amount": amount, "currency": cust["currency"]
        }, sort_keys=True).encode()).hexdigest()
        idempotency_keys[idem_key] = {
            "request_hash": body_hash,
            "response": payment,
            "status_code": 201,
            "created_at": created.isoformat(),
        }

        # Ledger entries for the payment lifecycle
        ledger_entries.append({
            "event_id": f"evt_{i:06d}_created",
            "type": "payment.created",
            "ref": pid,
            "amount": amount,
            "currency": cust["currency"],
            "merchant_id": "m_001",
            "provider": None,
            "correlation_id": f"corr_{i:06d}",
            "timestamp": created.isoformat(),
            "metadata": payment,
        })

        if state in ("authorized", "captured", "settled", "declined"):
            t = created + timedelta(seconds=rng.randint(1, 30))
            event_type = "payment.authorized" if state != "declined" else "payment.declined"
            ledger_entries.append({
                "event_id": f"evt_{i:06d}_auth",
                "type": event_type,
                "ref": pid,
                "amount": amount,
                "currency": cust["currency"],
                "merchant_id": "m_001",
                "provider": provider,
                "correlation_id": f"corr_{i:06d}",
                "timestamp": t.isoformat(),
                "metadata": {**payment, "provider_ref": provider_ref},
            })

        if state in ("captured", "settled"):
            t = created + timedelta(minutes=rng.randint(5, 60))
            ledger_entries.append({
                "event_id": f"evt_{i:06d}_capture",
                "type": "payment.captured",
                "ref": pid,
                "amount": amount,
                "currency": cust["currency"],
                "merchant_id": "m_001",
                "provider": provider,
                "correlation_id": f"corr_{i:06d}",
                "timestamp": t.isoformat(),
                "metadata": {**payment, "provider_ref": provider_ref},
            })

        if state == "settled":
            t = created + timedelta(hours=rng.randint(24, 72))
            ledger_entries.append({
                "event_id": f"evt_{i:06d}_settle",
                "type": "payment.settled",
                "ref": pid,
                "amount": amount,
                "currency": cust["currency"],
                "merchant_id": "m_001",
                "provider": provider,
                "correlation_id": f"corr_{i:06d}",
                "timestamp": t.isoformat(),
                "metadata": {**payment, "state": "settled", "provider_ref": provider_ref},
            })

    _write_json("idempotency/payments_store.json", payments)
    _write_json("idempotency/idempotency_keys.json", idempotency_keys)
    _write_jsonl("ledger/payments.jsonl", ledger_entries)
    print(f"  Payments: {len(payments)} with {len(ledger_entries)} ledger entries")

    # === Generate Refunds ===
    refund_ledger = []
    refunds = {}
    captured_payments = [p for p in payments.values() if p["state"] in ("captured", "settled")]

    for i, payment in enumerate(rng.sample(captured_payments, min(8, len(captured_payments)))):
        rid = f"ref_{i:06d}"
        refund_amount = payment["amount"] if rng.random() > 0.3 else rng.randint(100, payment["amount"])
        state = rng.choice(["pending_approval", "succeeded", "succeeded", "failed"])
        created = datetime.fromisoformat(payment["created_at"]) + timedelta(hours=rng.randint(2, 48))

        refund = {
            "id": rid,
            "payment_id": payment["id"],
            "amount": refund_amount,
            "currency": payment["currency"],
            "state": state,
            "reason": rng.choice(["Customer requested", "Duplicate charge", "Product return", "Service issue"]),
            "requested_by": "m_001",
            "approved_by": "m_002" if state in ("succeeded", "failed") else None,
            "merchant_id": "m_001",
            "correlation_id": f"corr_ref_{i:06d}",
            "created_at": created.isoformat(),
            "updated_at": created.isoformat(),
        }
        refunds[rid] = refund

        refund_ledger.append({
            "event_id": f"evt_ref_{i:06d}",
            "type": f"refund.{state}",
            "ref": rid,
            "amount": refund_amount,
            "currency": payment["currency"],
            "merchant_id": "m_001",
            "correlation_id": f"corr_ref_{i:06d}",
            "timestamp": created.isoformat(),
            "metadata": refund,
        })

    _write_json("idempotency/refunds_store.json", refunds)
    _write_jsonl("ledger/refunds.jsonl", refund_ledger)
    print(f"  Refunds: {len(refunds)}")

    # === Generate Disputes ===
    dispute_ledger = []
    disputes = {}
    disputable = [p for p in payments.values() if p["state"] in ("captured", "settled")]

    for i, payment in enumerate(rng.sample(disputable, min(5, len(disputable)))):
        did = f"dsp_{i:06d}"
        state = rng.choice(["opened", "under_review", "won", "lost"])
        created = datetime.fromisoformat(payment["created_at"]) + timedelta(hours=rng.randint(24, 120))

        dispute = {
            "id": did,
            "payment_id": payment["id"],
            "amount": payment["amount"],
            "state": state,
            "reason": rng.choice(DISPUTE_REASONS),
            "evidence": "Transaction receipt and delivery confirmation" if state in ("under_review", "won", "lost") else None,
            "merchant_id": "m_001",
            "correlation_id": f"corr_dsp_{i:06d}",
            "created_at": created.isoformat(),
            "updated_at": created.isoformat(),
        }
        disputes[did] = dispute

        dispute_ledger.append({
            "event_id": f"evt_dsp_{i:06d}",
            "type": f"dispute.{state}",
            "ref": did,
            "amount": payment["amount"],
            "merchant_id": "m_001",
            "correlation_id": f"corr_dsp_{i:06d}",
            "timestamp": created.isoformat(),
            "metadata": dispute,
        })

    _write_json("idempotency/disputes_store.json", disputes)
    _write_jsonl("ledger/disputes.jsonl", dispute_ledger)
    print(f"  Disputes: {len(disputes)}")

    # === Provider States ===
    for pid in ["providerA", "providerB"]:
        _write_json(f"providers/{pid}_state.json", {
            "provider_id": pid,
            "circuit_state": "closed",
            "failure_count": 0,
            "success_count": rng.randint(20, 50),
            "total_requests": rng.randint(25, 60),
            "last_success_at": datetime(2026, 2, 9).isoformat(),
            "last_failure_at": None,
            "half_open_calls": 0,
        })
        _write_json(f"providers/{pid}_sim.json", {
            "provider_id": pid,
            "total_requests": rng.randint(25, 60),
            "total_successes": rng.randint(20, 50),
            "total_failures": rng.randint(0, 5),
            "last_request_at": datetime(2026, 2, 9).isoformat(),
        })
    print("  Provider states: 2")

    # === Settlement CSV ===
    settled_entries = [e for e in ledger_entries if e["type"] in ("payment.captured", "payment.settled")]
    settlement_rows = []
    for e in settled_entries:
        meta = e.get("metadata", {})
        settlement_rows.append({
            "payment_id": e["ref"],
            "provider_ref": meta.get("provider_ref", ""),
            "amount": e["amount"],
            "currency": e["currency"],
            "type": e["type"],
            "status": "settled",
            "settled_at": e["timestamp"],
        })

    # Inject a settlement mismatch for demo
    if settlement_rows:
        mismatch_row = rng.choice(settlement_rows)
        mismatch_row["amount"] = int(mismatch_row["amount"]) - rng.randint(100, 500)

    csv_path = os.path.join(DATA_DIR, "settlement", "settlement_2026-02-09.csv")
    headers = ["payment_id", "provider_ref", "amount", "currency", "type", "status", "settled_at"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(settlement_rows)
    print(f"  Settlement CSV: {len(settlement_rows)} rows (1 mismatch injected)")

    # === Reconciliation Report ===
    # Build quick reconciliation
    ledger_amounts = {}
    for e in ledger_entries:
        if e["type"] in ("payment.captured", "payment.settled"):
            ledger_amounts[e["ref"]] = e["amount"]

    settle_amounts = {}
    for row in settlement_rows:
        settle_amounts[row["payment_id"]] = int(row["amount"])

    mismatches = []
    matched = 0
    for pid in set(ledger_amounts) | set(settle_amounts):
        la = ledger_amounts.get(pid)
        sa = settle_amounts.get(pid)
        if la is not None and sa is not None and la != sa:
            mismatches.append({
                "payment_id": pid,
                "ledger_amount": la,
                "settlement_amount": sa,
                "diff": la - sa,
                "issue": "amount_mismatch",
            })
        elif la == sa:
            matched += 1

    recon_report = {
        "date": "2026-02-09",
        "status": "mismatches_found" if mismatches else "clean",
        "total_ledger": sum(ledger_amounts.values()),
        "total_settlement": sum(settle_amounts.values()),
        "diff": sum(ledger_amounts.values()) - sum(settle_amounts.values()),
        "matched": matched,
        "mismatched": len(mismatches),
        "missing_from_settlement": 0,
        "missing_from_ledger": 0,
        "mismatches": mismatches,
        "generated_at": datetime.utcnow().isoformat(),
    }
    _write_json("reconciliation/reconciliation_report_2026-02-09.json", recon_report)
    print(f"  Reconciliation: {matched} matched, {len(mismatches)} mismatches")

    # === Metrics ===
    metrics = []
    for i in range(100):
        metrics.append({
            "timestamp": (base_time + timedelta(minutes=i * 5)).timestamp(),
            "method": rng.choice(["GET", "POST"]),
            "path": rng.choice(["/payment-intents", "/refunds", "/disputes", "/health"]),
            "status_code": rng.choice([200, 200, 200, 201, 400, 500]),
            "duration_ms": round(rng.uniform(5, 500), 2),
            "correlation_id": f"corr_metric_{i:04d}",
        })
    _write_jsonl("metrics/service_metrics.jsonl", metrics)
    print(f"  Metrics: {len(metrics)} entries")

    print("\nSeed data generation complete!")
    print(f"Data directory: {DATA_DIR}")


# === File writers ===

def _write_json(rel_path: str, data):
    path = os.path.join(DATA_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _write_jsonl(rel_path: str, records: list):
    path = os.path.join(DATA_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")


if __name__ == "__main__":
    seed_all()
