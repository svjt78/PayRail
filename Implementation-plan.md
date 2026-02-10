The plan covers a 7-phase implementation of ~65 files across 5 Dockerized services:

Phase 0: Foundation — shared utilities (atomic file I/O, Pydantic models, Fernet crypto, middleware), Docker configs, root .env
Phase 1: Vault Service — tokenization, encryption, key rotation, access logging
Phase 2: Provider Simulator — dual provider profiles, failure injection, HMAC webhooks, settlement CSV
Phase 3: API Gateway — payment lifecycle, refunds (maker-checker), disputes, idempotency, routing/failover, circuit breaker, ledger-first writes
Phase 4: Ledger Jobs — outbox dispatcher, settlement generator, reconciliation
Phase 5: Next.js Merchant Console — dashboard, payments, refunds, disputes, provider health, settlements, reconciliation, audit
Phase 6: Seed data generator, Docker finalization, README
Claude’s Plan
PayRail - Production-Grade Payment Gateway Demo
Context
Build a complete production-grade payment gateway simulator from scratch. The project demonstrates real-world payment engineering patterns (ledger-first accounting, idempotency, event outbox, tokenization vault, reconciliation, provider failover) using file-based storage only (no database). Fully Dockerized with hot reload, single root .env, and a Next.js merchant console UI.

Architecture Decisions
Separate services on separate internal ports: api-gateway (8026, exposed), vault-service (8027, internal), provider-sim (8028, internal), ledger-jobs (no HTTP). Mirrors real PCI-scoped separation.
Next.js Route Handlers as BFF: Frontend calls api-gateway via Next.js API routes (server-side), which inject X-Merchant-Id/X-Role headers. No separate BFF service needed.
Outbox dispatcher inside ledger-jobs: All background loops (outbox, settlement, reconciliation) run as async tasks in one process.
Implementation Phases
Phase 0: Foundation (~15 files)
Step	Files	Description
0.1	.env, docker-compose.yml, .gitignore	Root config: ports (3026/8026), service URLs, vault key, webhook secret, seed=42
0.2	backend/shared/{__init__,file_store,models,crypto,correlation,middleware}.py	Shared utils: atomic file I/O with filelock + temp-file-replace pattern; Pydantic domain models & state machine enums; Fernet encryption with MultiFernet rotation; correlation ID context var; RBAC/correlation/metrics middleware
0.3	Each service's Dockerfile + requirements.txt (×4)	Python 3.12-slim base, shared mounted at /app/shared, PYTHONPATH=/app:/app/shared
0.4	scripts/init_data.py, data/.gitkeep	Initialize data subdirectories
Phase 1: Vault Service (~3 files)
backend/vault_service/main.py — FastAPI app (internal only, no RBAC middleware)

Endpoint	Purpose
POST /tokenize	PAN → encrypt → store in tokens.json + encrypted_cards.json → return tok_xxx
POST /detokenize	Token → return last-four only, log access
POST /charge-token	Token → return decrypted PAN (internal use for provider charging)
POST /rotate-keys	Generate new Fernet key, prepend to keys.json
GET /health	Health check
Every access logged to data/vault/access_log.jsonl.

Phase 2: Provider Simulator (~4 files)
backend/provider_sim/main.py + failure_injection.py

Endpoint	Purpose
POST /providers/{id}/authorize	Simulate authorization (providerA: 95% success, providerB: 90%)
POST /providers/{id}/capture	Simulate capture
POST /providers/{id}/refund	Simulate refund
POST /providers/{id}/inject-failure	Configure failure rates (timeout, decline, error, duplicate webhook)
GET /providers/{id}/state	Return circuit breaker / health state
GET /providers/{id}/settlement	Generate settlement CSV for date
HMAC-signed webhooks sent to api-gateway callback URL
Deterministic failures via random.Random(seed)
Two provider profiles: providerA (Stripe-like) and providerB (Adyen-like)
Phase 3: API Gateway (~18 files)
backend/api_gateway/ — Main service, largest component

Routers:

routers/payments.py — Full payment lifecycle: create (idempotency-key required, ledger-first write), authorize (tokenize → route → call provider → failover), capture, cancel. List/get with filters.
routers/refunds.py — Maker-checker: create (PENDING_APPROVAL) → approve (different user) → process via provider. Reject path.
routers/disputes.py — Open, submit evidence, resolve (won/lost).
routers/webhooks.py — POST /webhooks/provider with HMAC validation, state update, outbox event.
routers/health.py — Service health, provider health board, metrics.
routers/audit.py — Audit trail for payments, vault access log, JSON export.
Services:

services/idempotency.py — Key→hash→cached-response in idempotency_keys.json. Reject mismatched retries (422).
services/routing.py — Select provider by: country rules, amount rules, circuit breaker state, cost table. Failover to secondary.
services/circuit_breaker.py — File-backed (provider state JSON). CLOSED→OPEN (after N failures)→HALF_OPEN (after timeout)→CLOSED.
services/ledger.py — Append-only JSONL writes. Replay entries to compute current state. Emit outbox events.
services/provider_client.py — Async HTTP client (httpx) with circuit breaker integration, timeout handling.
services/state_machine.py — Validate transitions against PAYMENT_TRANSITIONS, REFUND_TRANSITIONS, DISPUTE_TRANSITIONS maps.
Request/Response models: models/requests.py, models/responses.py

Phase 4: Ledger Jobs (~4 files)
backend/ledger_jobs/main.py — Three async loops:

Outbox Dispatcher (every 5s): Read events.jsonl → filter via processed_events.json → HMAC-sign → send webhook → mark processed. 3 retries with exponential backoff, then DLQ.
Settlement Generator (hourly/on-demand): Read captured payments from ledger → group by date → write settlement_YYYY-MM-DD.csv.
Reconciliation (hourly/on-demand): Compare ledger totals vs settlement CSV per payment_id → write reconciliation_report_YYYY-MM-DD.json with matched/mismatched/missing counts.
Phase 5: Frontend - Next.js Merchant Console (~30 files)
frontend/ — Next.js 14 App Router, Tailwind CSS, SWR for data fetching

Pages:

Route	Features
/ (Dashboard)	Summary cards (total payments, amount, success rate, pending refunds, open disputes), recent activity feed, provider status
/payments	Searchable/filterable table, state badges (color-coded), "New Payment" modal
/payments/[id]	Payment detail, visual state timeline, ledger entries, action buttons (authorize/capture/refund)
/refunds	Approval queue (pending) + all refunds table, inline approve/reject
/refunds/[id]	Refund detail with maker-checker info
/disputes	Dispute list, evidence submission
/disputes/[id]	Dispute detail, resolve actions
/providers	Health board with circuit breaker status, failure injection controls
/settlements	Date picker, settlement CSV table, download button
/reconciliation	Report viewer with mismatch details
/audit	Audit log viewer with export
API Routes (src/app/api/*/route.ts): Proxy layer injecting X-Merchant-Id and X-Role headers server-side.

Components: Sidebar, PaymentCard, StateTimeline, ProviderHealthCard, RefundApprovalCard, DisputeCard, SettlementTable, ReconciliationReport, SearchBar, Pagination, Badge, Modal

Phase 6: Seed Data, Docker Finalization & README (~3 files)
scripts/seed_data.py: Deterministic (seed=42) generator for: Luhn-valid PANs with BIN table, 20 customers, 40 cards, 50 payments across states, sample refunds/disputes, settlement CSV, vault tokens, provider states, idempotency keys.
docker-compose.yml update: Add seed profile service.
README.md: Architecture overview, quick start (docker compose up, seed command), service URLs, 5 demo scenario walkthroughs, file inspection guide.
File Storage Layout

data/
  ledger/          payments.jsonl, refunds.jsonl, disputes.jsonl
  vault/           tokens.json, encrypted_cards.json, access_log.jsonl, keys.json
  providers/       providerA_state.json, providerB_state.json
  settlement/      settlement_YYYY-MM-DD.csv
  metrics/         service_metrics.jsonl
  outbox/          events.jsonl, processed_events.json
  idempotency/     idempotency_keys.json
  reconciliation/  reconciliation_report_YYYY-MM-DD.json
Total File Count: ~65 files
Verification Plan
docker compose up --build — all 5 services start cleanly
docker compose --profile seed run seed — data populates
http://localhost:8026/docs — Swagger UI accessible
Payment lifecycle via curl: create → authorize → capture (verify ledger-first writes)
Duplicate POST with same Idempotency-Key → same response returned
Refund maker-checker: create as operator, approve as different user
Inject failures via provider-sim → circuit breaker opens → failover triggers
Verify vault: PAN encrypted in files, only token in payment records
Provider webhook → api-gateway receives → state updates
Settlement CSV generated, reconciliation report shows matches/mismatches
http://localhost:3026 — all UI pages render with data
Modify a .py file → Uvicorn reloads automatically
Trace correlation ID across service logs