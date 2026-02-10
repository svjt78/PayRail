# PayRail --- Production‑Grade Payment Gateway Demo (File‑Based)

## Objective

Demonstrate a realistic, production‑grade payment gateway with: -
Correctness (idempotency, state machines, reconciliation) - Reliability
(outbox, retries, DLQ) - Security boundaries (tokenization, PCI‑style
vault) - Observability & ops tooling - **No database** --- JSON/CSV
files only - Fully synthetic PCI/payment data

------------------------------------------------------------------------

## Architecture Overview

### Services (Dockerized)

1.  **api-gateway (FastAPI)**
    -   PaymentIntent lifecycle\
    -   Refunds / disputes\
    -   Webhook ingestion\
    -   Ledger writer
2.  **provider-sim**
    -   Fake processors (Stripe‑like / Adyen‑like)\
    -   Webhook emitter\
    -   Failure injection
3.  **ledger-service**
    -   JSONL event store\
    -   CSV settlement generator\
    -   Reconciliation jobs
4.  **vault-service**
    -   Tokenization\
    -   Encrypted PAN storage\
    -   Access logs
5.  **ui-console (Next.js)**
    -   Merchant dashboard\
    -   Refunds & disputes\
    -   Health metrics\
    -   Reconciliation reports

------------------------------------------------------------------------

## File‑Based Storage Strategy

    /data
      /ledger
         payments.jsonl
         refunds.jsonl
         disputes.jsonl
      /vault
         tokens.json
         encrypted_cards.json
         access_log.jsonl
      /providers
         providerA_state.json
         providerB_state.json
      /settlement
         settlement_2026‑02‑09.csv
      /metrics
         service_metrics.jsonl

-   **JSONL** = append‑only event streams
-   **CSV** = bank statements & payouts
-   **Nightly jobs** regenerate settlement files

------------------------------------------------------------------------

## Synthetic Data Generation

### PCI‑Like Card Generator

-   Luhn‑valid numbers
-   Fake BIN tables
-   Random expiry/CVV
-   Deterministic seeds for replay

### Customer Generator

-   Name / email / IP
-   Geo & MCC
-   Velocity patterns

### Fraud / Failure Injection

-   Timeout %
-   Decline reasons
-   Duplicate webhook sends
-   Settlement mismatches

------------------------------------------------------------------------

## Core Domain Model

### PaymentIntent

    {
      "id": "pi_123",
      "amount": 1099,
      "currency": "USD",
      "state": "authorized",
      "merchant_id": "m_001",
      "idempotency_key": "abc123",
      "provider": "providerA"
    }

### Ledger Entry

    {
      "event_id": "evt_999",
      "type": "payment.captured",
      "ref": "pi_123",
      "timestamp": "...",
      "hash": "..."
    }

------------------------------------------------------------------------

## State Machines

Payment: created → authorized → captured → settled\
Failure states: declined, reversed, chargeback

Dispute: opened → under_review → won / lost

------------------------------------------------------------------------

## API Surface

### POST /payment-intents

-   Requires Idempotency-Key
-   Writes ledger first

### POST /payment-intents/{id}/capture

### POST /refunds

### POST /webhooks/provider

### GET /ledger/{id}

------------------------------------------------------------------------

## Idempotency Implementation

-   Map keys to request hashes in: `idempotency_keys.json`
-   Reject mismatched retries
-   Return cached response

------------------------------------------------------------------------

## Eventing & Outbox

-   Append domain event to JSONL
-   Dispatcher reads & sends webhook
-   De‑dup via `processed_events.json`

------------------------------------------------------------------------

## Reconciliation Job

1.  Load ledger totals
2.  Parse settlement CSV
3.  Compare by payment_id
4.  Emit `reconciliation_report.json`
5.  Flag mismatches in UI

------------------------------------------------------------------------

## Vault & Tokenization

### Flow

1.  UI sends PAN → vault
2.  Vault stores encrypted value
3.  Returns `tok_xxx`
4.  Gateway charges token

### Encryption (Demo)

-   Fernet symmetric key
-   Key rotation file: `keys.json`

### Access Logs

-   Every lookup logged with purpose

------------------------------------------------------------------------

## Routing & Failover

Rules engine: - Country - Amount - Provider health - Cost table

Circuit breaker: - Stored in provider state JSON - Trips after error %

------------------------------------------------------------------------

## Observability

Metrics JSONL: - latency_ms - retries - webhook_lag - error_rate

Correlation IDs in all logs.

------------------------------------------------------------------------

## Merchant Console Features

-   Search payments
-   Refund workflow with approval
-   Dispute review
-   Provider health board
-   Settlement viewer
-   Audit export (PDF/JSON)

------------------------------------------------------------------------

## Demo Scenarios

1.  Duplicate submit → idempotency saves day
2.  Provider outage → failover
3.  Settlement mismatch → flagged
4.  Token audit trail
5.  Chargeback lifecycle

------------------------------------------------------------------------

## Non‑Goals

-   Real PCI compliance
-   External processors
-   Production KMS

------------------------------------------------------------------------

## Why This Looks "Production Grade"

-   Immutable ledger
-   Replayable events
-   Clear security boundary
-   Ops tooling
-   Reconciliation
-   Failure injection

------------------------------------------------------------------------

## Stretch Goals

-   Multi‑agent ops assistants:
    -   auto‑triage failures
    -   explain reconciliation
    -   draft dispute responses
-   SLO dashboards
-   Canary routing

------------------------------------------------------------------------

## Docker Expectations

-   docker-compose.yml
-   Hot reload
-   Mounted /data volume
-   One .env for all services

------------------------------------------------------------------------

## Interview Talking Points

-   Ledger‑first design
-   Outbox pattern without DB
-   Tokenization boundary
-   Reconciliation importance
-   Failover economics
