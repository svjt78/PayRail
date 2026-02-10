# Dispute Workflow (Chargeback Lifecycle)

This document describes how disputes work in PayRail, including API endpoints, state transitions, ledger/outbox behavior, and persistence.

## Overview

Disputes model chargebacks against **captured or settled** payments. A dispute:

- Starts in `opened`
- Moves to `under_review` after evidence is submitted
- Resolves as `won` or `lost`

When a dispute is opened for a captured/settled payment, the payment state is automatically moved to `chargeback`.

## State Machine

Dispute states and allowed transitions (from `backend/shared/models.py`):

```
opened  -> under_review -> won
                      -> lost
```

Any other transition is rejected with HTTP `409` via `validate_dispute_transition` in `backend/api_gateway/services/state_machine.py`.

## API Endpoints

All dispute endpoints are served by the API Gateway (`backend/api_gateway/routers/disputes.py`).

- `POST /disputes` — open a dispute
- `GET /disputes` — list disputes
- `GET /disputes/{id}` — get dispute + ledger entries
- `POST /disputes/{id}/submit-evidence` — move to `under_review`
- `POST /disputes/{id}/resolve` — resolve as `won` or `lost`

## Workflow Details

### 1) Open a Dispute

**Endpoint:** `POST /disputes`

**Key behaviors:**
- Idempotency is enforced (`Idempotency-Key` header).
- Payment must exist; otherwise `404`.
- Dispute is created with:
  - `state = opened`
  - `reason`, `amount`, `merchant_id`, `correlation_id`
- A ledger entry is written first (`dispute.opened`).
- The dispute is stored in `data/idempotency/disputes_store.json`.
- An outbox event is emitted: `dispute.opened`.
- If the payment state is `captured` or `settled`, it is updated to `chargeback`.

**Side effects:**
- Payment state change to `chargeback` is performed only when opening a dispute on a captured/settled payment.

### 2) Submit Evidence

**Endpoint:** `POST /disputes/{id}/submit-evidence`

**Key behaviors:**
- Idempotency is enforced.
- State transition must be `opened -> under_review`.
- Evidence text is stored on the dispute (`evidence`).
- A ledger entry is written: `dispute.under_review`.
- An outbox event is emitted: `dispute.under_review`.

### 3) Resolve the Dispute

**Endpoint:** `POST /disputes/{id}/resolve`

**Request field:** `outcome` must be `won` or `lost`.

**Key behaviors:**
- Idempotency is enforced.
- State transition must be `under_review -> won` or `under_review -> lost`.
- Dispute state is updated and stored.
- A ledger entry is written: `dispute.won` or `dispute.lost`.
- An outbox event is emitted: `dispute.won` or `dispute.lost`.

## Ledger and Outbox

- Ledger entries are written **first** for each dispute event (`dispute.opened`, `dispute.under_review`, `dispute.won`, `dispute.lost`).
- Each ledger entry includes `merchant_id`, `amount`, `correlation_id`, and full dispute metadata.
- Outbox events mirror these ledger events to support webhook delivery.

## Persistence

Dispute data is stored in file-based JSON/JSONL:

- `data/idempotency/disputes_store.json` — current dispute state (latest snapshot)
- `data/ledger/disputes.jsonl` — immutable ledger entries (event history)

Payment records are stored in:

- `data/idempotency/payments_store.json`

## Audit and UI

- Audit trail for disputes is accessible via `GET /audit/disputes` (API Gateway).
- The Merchant Console has Disputes list + detail views (`/disputes`, `/disputes/{id}`), including evidence submission and resolution.

## Error Handling Summary

- `404` — payment or dispute not found
- `409` — invalid state transition
- `400` — invalid resolution outcome
- `422` — idempotency conflict

## Reference Files

- Dispute API: `backend/api_gateway/routers/disputes.py`
- State machine: `backend/api_gateway/services/state_machine.py`
- Models and transitions: `backend/shared/models.py`
- Ledger service: `backend/api_gateway/services/ledger.py`
