# Refund Workflow (Maker-Checker + Provider Execution)

This document explains how refunds work in PayRail, who approves them, and when the provider is actually called.

## 1. Refund Request Created

**What it means**
- A refund request is recorded and placed in a **pending approval** state.

**Who initiates it**
- **Merchant (operator)** via UI or API.

**What happens**
- Refund is created with state `pending_approval`.
- A `refund.created` ledger entry is written.
- An outbox event is emitted (for reliable delivery/audit).

**Provider involvement**
- **None.** No provider API call is made at this step.

---

## 2. Approval or Rejection (Maker-Checker)

**What it means**
- A **different merchant user** (approver) must approve or reject the refund.

**Who initiates it**
- **Merchant (approver)** via UI or API.

**Why this exists**
- Prevents a single user from creating and approving a refund (fraud control).

---

## 3. Provider Execution (Only After Approval)

### If Approved
**What happens**
- API gateway calls the provider refund API:
  - `POST /providers/{provider_id}/refund`
- If provider succeeds: refund becomes `succeeded`.
- If provider fails: refund becomes `failed`.

**Ledger entries**
- `refund.succeeded` or `refund.failed`

**Provider involvement**
- **Yes, only after approval.**

### If Rejected
**What happens**
- Refund becomes `failed` (rejected).
- No provider call is made.

**Ledger entry**
- `refund.failed` (with rejection reason)

**Provider involvement**
- **None.**

---

## 4. Webhook / Outbox Events

You may see `webhook.refund.*` entries in the audit log.  
These are **internal outbox deliveries**, not necessarily provider callbacks.

---

## Quick Summary

```
Created (pending_approval) → Approved → Provider Refund → Succeeded/Failed
Created (pending_approval) → Rejected → Failed (no provider call)
```

---

## Where This Is Implemented

- Refund API: `backend/api_gateway/routers/refunds.py`
- Provider client: `backend/api_gateway/services/provider_client.py`
- Provider simulator: `backend/provider_sim/main.py`
- Ledger & audit: `backend/api_gateway/services/ledger.py`, `backend/api_gateway/routers/audit.py`
