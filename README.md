# PayRail

**A production-grade payment gateway simulator demonstrating enterprise payment processing patterns — built entirely with file-based storage (no database required).**

PayRail implements the same architectural patterns used by real-world payment processors like Stripe, Adyen, and Square: ledger-first event sourcing, PCI-compliant tokenization, circuit breakers, idempotency, maker-checker approval workflows, and end-to-end reconciliation. It runs as 5 Dockerized microservices with a Next.js merchant console.

---

## Table of Contents

- [Architecture](#architecture)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Services](#services)
- [API Reference](#api-reference)
- [Payment Lifecycle](#payment-lifecycle)
- [Refund Workflow](#refund-workflow)
- [Dispute Management](#dispute-management)
- [Tokenization Vault](#tokenization-vault)
- [Provider Routing & Circuit Breakers](#provider-routing--circuit-breakers)
- [Reconciliation & Settlement](#reconciliation--settlement)
- [Security & Access Control](#security--access-control)
- [Data Models](#data-models)
- [File Storage Layout](#file-storage-layout)
- [Frontend (Merchant Console)](#frontend-merchant-console)
- [Configuration](#configuration)
- [Demo Scenarios](#demo-scenarios)
- [Tech Stack](#tech-stack)
- [Design Patterns Reference](#design-patterns-reference)
- [Further Reading](#further-reading)

---

## Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │              Docker Network (payrail)       │
                          │                                             │
┌──────────────┐          │  ┌──────────────────┐   ┌──────────────┐   │
│              │  HTTP     │  │                  │   │              │   │
│   Frontend   │─────────▶│  │   API Gateway    │──▶│ Provider Sim │   │
│  (Next.js)   │          │  │   (FastAPI)      │   │  (FastAPI)   │   │
│  Port 3026   │          │  │   Port 8026      │   │  Port 8028   │   │
│              │          │  │                  │   │              │   │
└──────────────┘          │  └───────┬──┬───────┘   └──────┬───────┘   │
                          │          │  │                   │           │
                          │          │  │   ┌───────────────┘           │
                          │          │  │   │  Webhooks (HMAC-signed)   │
                          │          │  │   │                           │
                          │  ┌───────▼──┴───────┐   ┌──────────────┐   │
                          │  │                  │   │              │   │
                          │  │  Vault Service   │   │ Ledger Jobs  │   │
                          │  │   (FastAPI)      │   │  (Python)    │   │
                          │  │   Port 8027      │   │  Background  │   │
                          │  │                  │   │              │   │
                          │  └──────────────────┘   └──────────────┘   │
                          │                                             │
                          │         ┌───────────────────────┐           │
                          │         │  /data (shared volume) │           │
                          │         │  JSONL + JSON + CSV    │           │
                          │         └───────────────────────┘           │
                          └─────────────────────────────────────────────┘
```

**Data flow:** Frontend calls API Gateway through Next.js API routes (BFF pattern). API Gateway orchestrates Vault and Provider services internally over Docker DNS. Ledger Jobs runs background loops for outbox dispatch, settlement generation, and reconciliation. All services share a mounted `/data` volume for file-based persistence.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Ledger-First Design** | Immutable JSONL event store — all state changes written to ledger before processing |
| **Idempotency** | All write endpoints require `Idempotency-Key` header; cached responses prevent duplicates (24h TTL) |
| **State Machines** | Strict lifecycle transitions for payments, refunds, and disputes |
| **Vault Tokenization** | Fernet-encrypted PAN storage with MultiFernet key rotation and full access audit trail |
| **Circuit Breakers** | Per-provider failure tracking with automatic failover (CLOSED → OPEN → HALF_OPEN) |
| **Provider Routing** | Priority-based selection: preferred → country → amount threshold → default → failover |
| **Reconciliation** | Automated comparison of ledger totals vs settlement CSVs with mismatch reporting |
| **Maker-Checker Refunds** | Refund requests require approval by a different user (fraud prevention) |
| **Webhook HMAC Validation** | All provider webhooks signed with HMAC-SHA256 and verified on receipt |
| **Outbox Pattern** | Reliable event delivery with retry (exponential backoff) and dead-letter queue |
| **Correlation IDs** | End-to-end distributed tracing across all services via `X-Correlation-Id` |
| **Atomic File I/O** | FileLock + temp-file-rename pattern prevents data corruption from concurrent writes |
| **Synthetic PCI Data** | Luhn-valid card numbers with deterministic seeding for reproducible demos |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ports 3026 and 8026 available

### Start

```bash
# 1. Start all services (with hot reload)
docker compose up --build

# 2. Seed demo data (in a second terminal)
docker compose --profile seed run seed

# 3. Open the merchant console
open http://localhost:3026

# 4. Explore the interactive API docs
open http://localhost:8026/docs
```

### Stop

```bash
docker compose down
```

### Reset Data

```bash
# Remove all generated data and re-seed
rm -rf data/*
docker compose --profile seed run seed
```

---

## Services

| Service | Port | Exposed | Description |
|---------|------|---------|-------------|
| **api-gateway** | 8026 | Yes | Main payment API — payments, refunds, disputes, webhooks, audit |
| **vault-service** | 8027 | No (internal) | Tokenization, PAN encryption, key rotation, access logging |
| **provider-sim** | 8028 | No (internal) | Simulated payment processors with configurable failure injection |
| **ledger-jobs** | — | No | Background: outbox dispatcher (5s), settlement generator (10s), reconciliation (1hr) |
| **frontend** | 3026 | Yes | Next.js merchant console with full operational visibility |

**Internal communication** uses Docker DNS (e.g., `http://vault-service:8027`). Only the API Gateway and Frontend are exposed to the host.

---

## API Reference

All write endpoints require the `Idempotency-Key` and `X-Merchant-Id` headers.

### Payments

```
POST   /payment-intents                    Create payment intent
GET    /payment-intents                    List payments (filterable by state, merchant_id)
GET    /payment-intents/{id}               Get payment with ledger history
POST   /payment-intents/{id}/authorize     Authorize with card PAN or existing token
POST   /payment-intents/{id}/capture       Capture authorized payment
POST   /payment-intents/{id}/cancel        Cancel / reverse payment
```

### Refunds

```
POST   /refunds                            Create refund request (enters approval queue)
GET    /refunds                            List refunds (filterable)
GET    /refunds/{id}                       Get refund with ledger history
POST   /refunds/{id}/approve              Approve refund — maker-checker enforced
POST   /refunds/{id}/reject               Reject refund request
```

### Disputes

```
POST   /disputes                           Open dispute on a captured payment
GET    /disputes                           List disputes
GET    /disputes/{id}                      Get dispute details
POST   /disputes/{id}/submit-evidence      Submit evidence (moves to under_review)
POST   /disputes/{id}/resolve             Resolve dispute (won / lost)
```

### Webhooks

```
POST   /webhooks/provider                  Receive HMAC-signed provider webhooks
```

### Operations

```
GET    /health                             API gateway health check
GET    /providers/health                   Provider circuit breaker status board
GET    /metrics                            Request latency and status metrics
GET    /ledger/{ref_id}                    Ledger entries for any entity
```

### Audit

```
GET    /audit/payments                     Payment audit trail
GET    /audit/refunds                      Refund audit trail
GET    /audit/disputes                     Dispute audit trail
GET    /audit/vault-access                 Vault access log (tokenize/detokenize/charge events)
GET    /audit/settlements                  Settlement CSV files
GET    /audit/reconciliation               Reconciliation reports
GET    /audit/export                       Full audit export (JSON)
```

### Vault (Internal Only)

```
POST   /tokenize                           PAN → encrypted storage + token
POST   /detokenize                         Token → last-four + metadata (no PAN)
POST   /charge-token                       Token → decrypted PAN (for provider charging)
POST   /rotate-keys                        Rotate encryption keys (MultiFernet)
GET    /access-log                         Vault access audit trail
GET    /health                             Vault health check
```

### Provider Simulator (Internal Only)

```
POST   /providers/{id}/authorize           Simulate authorization (success/decline)
POST   /providers/{id}/capture             Simulate capture
POST   /providers/{id}/refund              Simulate refund
GET    /providers/{id}/state               Get circuit breaker state
POST   /providers/{id}/inject-failure      Configure failure rates
```

---

## Payment Lifecycle

Payments follow a strict state machine with ledger-first writes at every transition.

```
                    ┌──────────┐
                    │ created  │
                    └────┬─────┘
                         │ authorize
                    ┌────▼─────┐       ┌──────────┐
                    │authorized│       │ declined  │
                    └────┬─────┘       └──────────┘
                         │ capture
                    ┌────▼─────┐
                    │ captured │──────────────┐
                    └────┬─────┘              │ dispute opened
                         │ settle             │
                    ┌────▼─────┐       ┌──────▼─────┐
                    │ settled  │       │ chargeback  │
                    └──────────┘       └────────────┘

   Any authorized/captured payment can also be:
                    ┌──────────┐
                    │ reversed │  (via cancel)
                    └──────────┘
```

| State | Meaning | Who Initiates |
|-------|---------|---------------|
| **created** | Payment intent recorded | Merchant (API/UI) |
| **authorized** | Funds reserved on cardholder's account | Merchant triggers, provider/bank executes |
| **captured** | Funds charged — payment is successful | Merchant triggers, provider/bank executes |
| **settled** | Finalized in settlement CSV, reconciled | Ledger Jobs (automatic) |
| **declined** | Authorization rejected by issuer | Provider response |
| **reversed** | Authorized payment cancelled before capture | Merchant triggers |
| **chargeback** | Dispute opened on captured payment | Dispute creation (automatic) |

Each transition writes an immutable ledger entry (`payment.created`, `payment.authorized`, etc.) and emits an outbox event for webhook delivery.

See [PAYMENT_WORKFLOW.md](PAYMENT_WORKFLOW.md) for a detailed walkthrough.

---

## Refund Workflow

Refunds use a **maker-checker pattern** — the user who creates the refund cannot be the one who approves it.

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐     ┌───────────┐
│ Refund Created   │────▶│ Pending Approval  │────▶│ Provider Call   │────▶│ Succeeded │
│ (by operator A) │     │ (maker-checker)   │     │ (after approve) │     └───────────┘
└─────────────────┘     └────────┬─────────┘     └────────┬────────┘
                                 │ reject                  │ provider fails
                                 ▼                         ▼
                          ┌──────────┐              ┌──────────┐
                          │  Failed  │              │  Failed  │
                          │(rejected)│              │(provider)│
                          └──────────┘              └──────────┘
```

- **No provider call is made** until the refund is approved
- Rejection records a reason but never contacts the provider
- The approver's identity (`X-Merchant-Id`) must differ from the requester's
- Partial refunds are supported (amount validated against original payment)

See [REFUND_WORKFLOW.md](REFUND_WORKFLOW.md) for details.

---

## Dispute Management

Disputes model the chargeback lifecycle against **captured or settled** payments.

```
opened  →  under_review  →  won / lost
```

| Action | Endpoint | Effect |
|--------|----------|--------|
| **Open dispute** | `POST /disputes` | Dispute created as `opened`; payment auto-transitions to `chargeback` |
| **Submit evidence** | `POST /disputes/{id}/submit-evidence` | Dispute moves to `under_review`; evidence text stored |
| **Resolve (won)** | `POST /disputes/{id}/resolve` | Merchant wins — funds retained |
| **Resolve (lost)** | `POST /disputes/{id}/resolve` | Merchant loses — funds returned to cardholder |

**Behavior details:**

- Idempotency is enforced on all dispute write endpoints
- A ledger entry is written **first** for each state change (`dispute.opened`, `dispute.under_review`, `dispute.won`, `dispute.lost`)
- Outbox events mirror ledger events for webhook delivery
- Invalid state transitions return `409`; invalid resolution outcomes return `400`
- Dispute data is persisted in `data/idempotency/disputes_store.json` (current state) and `data/ledger/disputes.jsonl` (immutable event history)

See [DISPUTE_WORKFLOW.md](DISPUTE_WORKFLOW.md) for the full walkthrough.

---

## Tokenization Vault

The Vault Service acts as a **PCI boundary**, isolating raw card data from the rest of the system.

```
                     PCI Boundary
                   ┌─────────────────────────────────┐
  PAN: 4111...1111 │  Vault Service                  │  Token: tok_a1b2c3...
  ───────────────▶ │  1. Encrypt PAN (Fernet)        │ ──────────────────▶
                   │  2. Store encrypted blob        │   (used everywhere
                   │  3. Return token (tok_...)       │    in the system)
                   │  4. Log access event            │
                   └─────────────────────────────────┘
```

**Core guarantees:**

- **Encryption at rest** — PANs encrypted with Fernet before storage
- **Key rotation** — MultiFernet supports versioned keys; old data stays decryptable
- **Token surrogates** — Only `tok_...` tokens appear in payment records, ledger, and logs
- **Access logging** — Every tokenize, detokenize, and charge-token call is logged with requester, purpose, and correlation ID
- **Minimal exposure** — Only `/charge-token` returns the actual PAN (for provider authorization); `/detokenize` returns only last-four and metadata
- **CVV never stored** — Follows PCI DSS rules (CVV discarded after authorization)

### VaultCrypto + Fernet/MultiFernet

The `VaultCrypto` class (`backend/shared/crypto.py`) wraps `cryptography.fernet.Fernet` and `MultiFernet`:

- **Key bootstrap** — On init, `_ensure_keys()` creates `data/vault/keys.json` with a generated Fernet key if missing
- **Encrypt** — `MultiFernet.encrypt()` always uses the **first** (newest) key
- **Decrypt** — `MultiFernet.decrypt()` tries keys in order until one succeeds
- **Rotate** — `rotate_key()` generates a new key and prepends it; old keys remain so existing ciphertext stays decryptable
- **No re-encryption** — Rotation does not re-encrypt existing data; old PANs are decrypted using their original key

Key storage: `data/vault/keys.json` — keys never leave the vault service over HTTP.

See [VAULT_OVERVIEW.md](VAULT_OVERVIEW.md) for the full explanation including encryption flow and key storage details.

---

## Provider Routing & Circuit Breakers

### Provider Profiles

| Provider | Model | Success Rate | Latency | Fee |
|----------|-------|-------------|---------|-----|
| **providerA** | Stripe-like | 95% | 100-300ms | 2.9% |
| **providerB** | Adyen-like | 90% | 200-500ms | 2.5% |

### Routing Decision Order

Evaluated top-to-bottom — first match wins:

1. **Preferred provider** — If explicitly requested and circuit allows it
2. **Country rules** — DE/FR/GB/JP → providerB; US/CA/AU → providerA
3. **Amount threshold** — >= $100 (10,000 cents) → providerB
4. **Default** — `providerA` (configurable via `DEFAULT_PROVIDER`)
5. **Failover** — `providerB` (if default circuit is OPEN)

If all providers are unavailable, authorization fails with an error.

### Circuit Breaker States

```
CLOSED ──(failures >= threshold)──▶ OPEN ──(recovery timeout)──▶ HALF_OPEN
   ▲                                                                 │
   └────────────────(success in half-open)───────────────────────────┘
                     │
              (failure in half-open)
                     │
                     ▼
                   OPEN
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CB_FAILURE_THRESHOLD` | 5 | Consecutive failures before opening circuit |
| `CB_RECOVERY_TIMEOUT` | 30s | Time before allowing a trial request |
| `CB_HALF_OPEN_MAX_CALLS` | 3 | Trial requests allowed in half-open state |

Circuit breaker state is persisted per-provider in `data/providers/{id}_state.json`.

### Failure Injection

The provider simulator supports configurable failure modes for testing resilience:

```json
{
  "timeout_rate": 0.0,
  "decline_rate": 0.05,
  "error_rate": 0.0,
  "duplicate_webhook_rate": 0.0,
  "settlement_mismatch_rate": 0.0,
  "latency_ms_min": 100,
  "latency_ms_max": 300
}
```

Inject failures from the UI at `/providers` or via `POST /providers/{id}/inject-failure`.

See [PROVIDER_SELECTION.md](PROVIDER_SELECTION.md) for full routing documentation.

---

## Reconciliation & Settlement

### Settlement Generation

The **ledger-jobs** service runs a settlement loop every 10 seconds:

1. Reads `ledger/payments.jsonl` for `payment.captured` events
2. Groups by date and generates `settlement/settlement_YYYY-MM-DD.csv`
3. Promotes captured payments to `settled` state in the ledger

**CSV format:**
```
payment_id,provider_ref,amount,currency,type,status,settled_at
pi_abc123,txn_123,5000,USD,payment.captured,settled,2026-02-09T12:35:10
```

### Reconciliation

Runs hourly, comparing ledger against settlement:

1. Sums all ledger amounts by payment_id
2. Sums all settlement CSV amounts by payment_id
3. Flags mismatches: amount differences, missing from settlement, missing from ledger
4. Generates `reconciliation/reconciliation_report_YYYY-MM-DD.json`

**Report structure:**
```json
{
  "date": "2026-02-09",
  "status": "mismatches_found",
  "total_ledger": 50000,
  "total_settlement": 50000,
  "matched": 10,
  "mismatched": 1,
  "missing_from_settlement": 0,
  "missing_from_ledger": 0,
  "mismatches": [
    {
      "payment_id": "pi_xyz",
      "ledger_amount": 2500,
      "settlement_amount": 2000,
      "diff": 500,
      "issue": "amount_mismatch"
    }
  ]
}
```

---

## Security & Access Control

### Merchant Identification

All write operations require the `X-Merchant-Id` header. The RBAC middleware enforces this on POST/PUT/PATCH/DELETE requests, enabling multi-tenant isolation.

### Role-Based Maker-Checker

The `X-Role` header (e.g., `operator`, `admin`) is used for maker-checker validation on refund approvals. The system ensures `requested_by != approved_by`.

### Webhook HMAC Validation

Provider webhooks are signed with HMAC-SHA256:

```
Header: X-Webhook-Signature: sha256=<hex_digest>
Secret: WEBHOOK_SECRET (from .env)
Validation: hmac.compare_digest() (constant-time comparison)
```

Invalid signatures are rejected with 401.

### Idempotency Protection

- Required `Idempotency-Key` header on all write endpoints
- Duplicate requests with the same key return the cached response
- Duplicate requests with the same key but different bodies are rejected (422)
- Keys expire after 24 hours

### Correlation IDs

- Format: `corr_<16-char hex>`
- Auto-generated if not provided via `X-Correlation-Id` header
- Propagated across all inter-service calls
- Stored in every ledger entry, outbox event, and audit record

---

## Data Models

### PaymentIntent

```json
{
  "id": "pi_abc123def456",
  "amount": 5000,
  "currency": "USD",
  "state": "captured",
  "merchant_id": "m_001",
  "customer_email": "customer@example.com",
  "description": "Order #123",
  "provider": "providerA",
  "token": "tok_a1b2c3...",
  "provider_ref": "txn_provider_123",
  "idempotency_key": "key-123",
  "correlation_id": "corr_abc123...",
  "created_at": "2026-02-09T12:34:56",
  "updated_at": "2026-02-09T12:35:10",
  "metadata": {}
}
```

### Refund

```json
{
  "id": "ref_abc123",
  "payment_id": "pi_abc123def456",
  "amount": 2500,
  "currency": "USD",
  "state": "approved",
  "reason": "Customer requested",
  "requested_by": "op_001",
  "approved_by": "op_002",
  "merchant_id": "m_001",
  "correlation_id": "corr_...",
  "created_at": "2026-02-09T12:40:00",
  "updated_at": "2026-02-09T12:45:00"
}
```

### Dispute

```json
{
  "id": "dsp_abc123",
  "payment_id": "pi_abc123def456",
  "amount": 5000,
  "state": "won",
  "reason": "Customer claims unauthorized",
  "evidence": "Order confirmation and delivery receipt",
  "merchant_id": "m_001",
  "correlation_id": "corr_...",
  "created_at": "2026-02-09T13:00:00",
  "updated_at": "2026-02-09T13:15:00"
}
```

### LedgerEntry (Immutable)

```json
{
  "event_id": "evt_abc123def456",
  "type": "payment.captured",
  "ref": "pi_abc123def456",
  "amount": 5000,
  "currency": "USD",
  "merchant_id": "m_001",
  "provider": "providerA",
  "correlation_id": "corr_...",
  "timestamp": "2026-02-09T12:35:10",
  "metadata": {}
}
```

### OutboxEvent

```json
{
  "event_id": "oevt_abc123",
  "type": "payment.captured",
  "payload": {},
  "correlation_id": "corr_...",
  "created_at": "2026-02-09T12:35:10"
}
```

---

## File Storage Layout

All data is stored in the shared `data/` volume as JSON, JSONL, and CSV files. No database is required.

```
data/
├── ledger/                          # Immutable event streams (append-only)
│   ├── payments.jsonl               #   Payment lifecycle events
│   ├── refunds.jsonl                #   Refund lifecycle events
│   └── disputes.jsonl               #   Dispute lifecycle events
│
├── vault/                           # PCI boundary — encrypted card storage
│   ├── tokens.json                  #   Token → encrypted PAN mapping
│   ├── encrypted_cards.json         #   Token → metadata (brand, last-four, expiry)
│   ├── access_log.jsonl             #   Access audit trail (immutable)
│   └── keys.json                    #   Fernet encryption keys (MultiFernet)
│
├── providers/                       # Provider state
│   ├── providerA_state.json         #   Circuit breaker state
│   ├── providerB_state.json         #   Circuit breaker state
│   ├── providerA_sim.json           #   Simulation config (failure rates)
│   └── providerB_sim.json           #   Simulation config (failure rates)
│
├── settlement/                      # Bank-style settlement files
│   └── settlement_YYYY-MM-DD.csv    #   Daily settlement CSV
│
├── reconciliation/                  # Recon reports
│   └── reconciliation_report_YYYY-MM-DD.json
│
├── outbox/                          # Reliable event delivery
│   ├── events.jsonl                 #   Pending outbox events
│   ├── processed_events.json        #   Deduplication tracking
│   └── processed_webhooks.json      #   Webhook deduplication
│
├── idempotency/                     # Request dedup + current state
│   ├── idempotency_keys.json        #   Idempotency cache (24h TTL)
│   ├── payments_store.json          #   Current payment states
│   ├── refunds_store.json           #   Current refund states
│   └── disputes_store.json          #   Current dispute states
│
└── metrics/                         # Observability
    └── service_metrics.jsonl        #   Request latency / status metrics
```

All file writes use **FileLock + atomic temp-file rename** to prevent corruption from concurrent access.

### Inspecting Data

```bash
# View payment ledger events
cat data/ledger/payments.jsonl | python3 -m json.tool --json-lines | head -50

# View vault tokens (PANs are encrypted — only ciphertext visible)
cat data/vault/tokens.json | python3 -m json.tool

# View settlement CSV
column -t -s, data/settlement/settlement_2026-02-09.csv

# View reconciliation report
cat data/reconciliation/reconciliation_report_2026-02-09.json | python3 -m json.tool

# View circuit breaker state
cat data/providers/providerA_state.json | python3 -m json.tool
```

---

## Frontend (Merchant Console)

The Next.js merchant console at `http://localhost:3026` provides full operational visibility.

| Page | Features |
|------|----------|
| **Dashboard** (`/`) | Summary cards, recent activity feed, provider status indicators |
| **Payments** (`/payments`) | Searchable/filterable table, state badges, new payment modal, detail view with visual timeline |
| **Refunds** (`/refunds`) | Approval queue with inline approve/reject, maker-checker enforcement |
| **Disputes** (`/disputes`) | List view, evidence submission form, resolution actions |
| **Providers** (`/providers`) | Circuit breaker status board, failure injection controls for testing |
| **Settlements** (`/settlements`) | Date picker, CSV table viewer, download |
| **Reconciliation** (`/reconciliation`) | Report viewer with mismatch highlighting |
| **Audit** (`/audit`) | Full audit log viewer with entity/vault-access filters, export |

The frontend uses **Next.js API routes as a BFF (Backend-for-Frontend)** layer — server-side routes proxy requests to the API Gateway, injecting `X-Merchant-Id`, `X-Role`, and `Idempotency-Key` headers transparently.

---

## Configuration

All configuration is managed through the root `.env` file.

### Ports

| Variable | Default | Description |
|----------|---------|-------------|
| `API_GATEWAY_PORT` | `8026` | API Gateway (exposed) |
| `VAULT_SERVICE_PORT` | `8027` | Vault Service (internal) |
| `PROVIDER_SIM_PORT` | `8028` | Provider Simulator (internal) |
| `FRONTEND_PORT` | `3026` | Next.js frontend (exposed) |

### Service URLs (Docker DNS)

| Variable | Default |
|----------|---------|
| `VAULT_SERVICE_URL` | `http://vault-service:8027` |
| `PROVIDER_SIM_URL` | `http://provider-sim:8028` |
| `API_GATEWAY_URL` | `http://api-gateway:8026` |

### Security

| Variable | Description |
|----------|-------------|
| `VAULT_MASTER_KEY` | Base64-encoded Fernet key for PAN encryption |
| `WEBHOOK_SECRET` | HMAC-SHA256 secret for webhook signing/verification |

### Circuit Breaker

| Variable | Default | Description |
|----------|---------|-------------|
| `CB_FAILURE_THRESHOLD` | `5` | Consecutive failures before opening circuit |
| `CB_RECOVERY_TIMEOUT` | `30` | Seconds before allowing trial request |
| `CB_HALF_OPEN_MAX_CALLS` | `3` | Trial requests in half-open state |

### Routing

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_PROVIDER` | `providerA` | Primary provider |
| `FAILOVER_PROVIDER` | `providerB` | Failover when primary circuit opens |

### Other

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `/app/data` | Shared data directory path |
| `SEED` | `42` | Deterministic seed for reproducible demo data |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Demo Scenarios

### 1. Idempotency (Duplicate Submit)

```bash
# First request — creates payment
curl -s -X POST http://localhost:8026/payment-intents \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: test-key-001" \
  -d '{"amount": 5000, "currency": "USD"}'

# Same request again — returns cached response (no duplicate created)
curl -s -X POST http://localhost:8026/payment-intents \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: test-key-001" \
  -d '{"amount": 5000, "currency": "USD"}'
```

### 2. Full Payment Lifecycle

```bash
# Create payment intent
PAYMENT=$(curl -s -X POST http://localhost:8026/payment-intents \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: lifecycle-001" \
  -d '{"amount": 2500, "currency": "USD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Created: $PAYMENT"

# Authorize with card
curl -s -X POST http://localhost:8026/payment-intents/$PAYMENT/authorize \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: auth-001" \
  -d '{"pan": "4111111111111111", "expiry": "12/28"}'

# Capture
curl -s -X POST http://localhost:8026/payment-intents/$PAYMENT/capture \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: cap-001"

# View ledger history
curl -s http://localhost:8026/ledger/$PAYMENT | python3 -m json.tool
```

### 3. Maker-Checker Refund

```bash
# Operator A creates refund
REFUND=$(curl -s -X POST http://localhost:8026/refunds \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: op_001" \
  -H "X-Role: operator" \
  -H "Idempotency-Key: refund-001" \
  -d "{\"payment_id\": \"$PAYMENT\", \"amount\": 1000, \"reason\": \"Partial refund\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Operator B (different user) approves
curl -s -X POST http://localhost:8026/refunds/$REFUND/approve \
  -H "X-Merchant-Id: op_002" \
  -H "X-Role: operator" \
  -H "Idempotency-Key: approve-001"
```

### 4. Settlement Mismatch

View the **Reconciliation** page in the UI — a mismatch is injected in the seed data to demonstrate the reconciliation report.

### 5. Vault Audit Trail

Check the **Audit** page with the "vault access" filter to see every tokenization and detokenization event with requester identity and purpose.

### 6. Chargeback Lifecycle

Open a dispute on a captured payment — the payment automatically transitions to the `chargeback` state:

```bash
curl -s -X POST http://localhost:8026/disputes \
  -H "Content-Type: application/json" \
  -H "X-Merchant-Id: m_001" \
  -H "Idempotency-Key: dispute-001" \
  -d "{\"payment_id\": \"$PAYMENT\", \"reason\": \"Unauthorized charge\"}"
```

### 7. Circuit Breaker & Failover

Use the **Providers** page to inject failures into `providerA`. After 5 consecutive failures, the circuit opens and traffic automatically fails over to `providerB`.

---

## Tech Stack

### Backend

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI + Uvicorn (hot reload) |
| Validation | Pydantic v2.10+ |
| Encryption | cryptography (Fernet / MultiFernet) |
| HTTP Client | httpx (async) |
| File Safety | filelock (atomic operations) |
| Tracing | contextvars (correlation ID propagation) |

### Frontend

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 14 (App Router) |
| UI | React 18 |
| Styling | Tailwind CSS |
| Data Fetching | SWR |
| Icons | Lucide React |
| Language | TypeScript |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Storage | JSON, JSONL, CSV (file-based) |
| Networking | Docker bridge network |
| Hot Reload | Uvicorn `--reload` + Next.js dev server |

---

## Design Patterns Reference

| Pattern | Where Used | Purpose |
|---------|-----------|---------|
| **Ledger-First (Event Sourcing)** | All state changes | Immutability, auditability, state replay |
| **Idempotency Keys** | All write endpoints | Safe retries, duplicate prevention |
| **State Machine** | Payment, Refund, Dispute | Enforced lifecycle transitions |
| **Tokenization** | Vault Service | PCI boundary, data protection |
| **Circuit Breaker** | Provider routing | Fault isolation, automatic failover |
| **Outbox Pattern** | Webhook delivery | Reliable event delivery, at-least-once semantics |
| **Maker-Checker** | Refund approvals | Fraud prevention, separation of duties |
| **HMAC Signing** | Webhook validation | Tamper-proof webhook verification |
| **BFF (Backend-for-Frontend)** | Next.js API routes | Header injection, API abstraction |
| **Atomic File I/O** | All file writes | Concurrency safety, corruption prevention |
| **Correlation IDs** | Cross-service tracing | Distributed observability |
| **Deterministic Seeding** | Demo data generation | Reproducible test scenarios |

---

## Further Reading

| Document | Description |
|----------|-------------|
| [PAYMENT_WORKFLOW.md](PAYMENT_WORKFLOW.md) | Detailed payment lifecycle explanation |
| [REFUND_WORKFLOW.md](REFUND_WORKFLOW.md) | Maker-checker refund approval process |
| [DISPUTE_WORKFLOW.md](DISPUTE_WORKFLOW.md) | Chargeback lifecycle, state machine, and error handling |
| [VAULT_OVERVIEW.md](VAULT_OVERVIEW.md) | Tokenization, encryption, VaultCrypto/Fernet/MultiFernet deep dive |
| [PROVIDER_SELECTION.md](PROVIDER_SELECTION.md) | Provider routing rules and configuration |
| [Swagger UI](http://localhost:8026/docs) | Interactive API documentation (when running) |
