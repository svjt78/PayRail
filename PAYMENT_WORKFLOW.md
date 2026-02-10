# Payment Workflow (Created → Authorized → Captured → Settled)

This document explains the PayRail payment lifecycle in plain terms, including what each step means, who is involved, and why it exists.

## 1. Created

**What it means**
- A payment request (Payment Intent) is recorded in the system.

**Who initiates it**
- **Merchant** (via UI or API).

**What happens**
- A `payment.created` ledger entry is written.
- The payment is stored with state `created`.

**Why it matters**
- This is the starting point for all payments and is safe to create multiple times because of idempotency.

---

## 2. Authorized (Reserve / Hold)

**What it means**
- The customer’s bank confirms the card is valid and **reserves** (holds) the funds.

**Who initiates it**
- **Merchant** clicks “Authorize” (or calls the API).

**Who performs it**
- **Provider/Processor** routes the request through the **card network** to the **issuing bank**.
- The **issuing bank** places a hold on the customer’s funds.

**What happens**
- Provider returns success/decline.
- A `payment.authorized` or `payment.declined` ledger entry is written.
- Provider also sends a webhook: `webhook.payment.authorized` or `webhook.payment.declined`.

**Why it matters**
- It ensures funds are available **before** the merchant completes the charge.
- The reserve is on the **payor’s** account (not the merchant’s).

---

## 3. Captured (Charge)

**What it means**
- The reserved funds are **actually charged**.

**Who initiates it**
- **Merchant** clicks “Capture” (or calls the API).

**Who performs it**
- **Provider/Processor** submits the capture through the card network to the issuing bank.
- The issuing bank deducts the funds.

**What happens**
- A `payment.captured` ledger entry is written.
- Provider sends a confirmation webhook: `webhook.payment.captured`.

**Why it matters**
- `captured` means the payment is **successful** from the merchant’s perspective.

---

## 4. Settled (Finalized / Reconciled)

**What it means**
- The captured payment is **finalized** in settlement and reconciliation.

**Who initiates it**
- **Ledger jobs** run automatically (demo interval is 10 seconds).

**What happens**
- A `payment.settled` ledger entry is written.
- A settlement CSV is generated.
- Reconciliation compares ledger totals vs settlement totals.

**Why it matters**
- Confirms money moved through the provider’s settlement cycle.
- Enables accurate reconciliation and reporting.

---

## Quick Summary

```
Created  →  Authorized  →  Captured  →  Settled
```

- **Authorize** = hold funds.
- **Capture** = take funds.
- **Settle** = finalize and reconcile.

---

## Where This Is Implemented

- Payment lifecycle API: `backend/api_gateway/routers/payments.py`
- Routing & provider selection: `backend/api_gateway/services/routing.py`
- Provider simulation: `backend/provider_sim/main.py`
- Settlement + reconciliation: `backend/ledger_jobs/settlement_generator.py`, `backend/ledger_jobs/reconciliation.py`
- Audit log: `backend/api_gateway/routers/audit.py`
