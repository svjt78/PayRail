# PayRail Implementation Agent Prompt

## Purpose

This document is a **build prompt** for an AI coding agent to implement
the PayRail production‑grade payment gateway demo using file‑based
storage, synthetic PCI data, Docker Compose, hot reload, and a single
root `.env`.

------------------------------------------------------------------------

## MASTER PROMPT

    You are an expert full-stack engineer and platform architect. Implement the “PayRail” demo app: a production-grade payment gateway simulator with ledger-first accounting, idempotency, event outbox, webhooks, tokenization vault, reconciliation, provider failover, and an ops/merchant console UI.

    CRITICAL TECHNICAL IMPERATIVES (must follow exactly):
    1) Next.js must run on port 3026.
    2) FastAPI must run on port 8026.
    3) Entire app must be fully dockerized and runnable via docker-compose.yml.
    4) There must be ONLY ONE .env file located at the repo root, and it must serve ALL services (frontend, backend, provider-sim, vault, ledger jobs). Do NOT create .env.example.
    5) Hot reload must be enabled for Next.js and FastAPI.
    6) NO database. All persistence must be file-based using JSON/JSONL/CSV only.
    7) All demo data must be synthetically generated, including PCI-like data (Luhn-valid PANs etc). Never use real card data.
    8) Deterministic seeds must be used for replayability.
    9) All write endpoints must support Idempotency-Key.

    DELIVERABLES:
    - Repo structure with frontend, backend services, docker-compose.yml, root .env, README.md.
    - Services: api-gateway, vault-service, provider-sim, ledger-jobs.
    - Next.js Merchant Console UI.

    PRODUCT SCOPE:
    Payment lifecycle, refunds, disputes, webhooks, reconciliation, routing, circuit breakers, audit trails, maker-checker refunds.

    FILE-BASED STORAGE:
    Use /app/data volume shared across services with JSON/CSV/JSONL.

    STATE MACHINES:
    Payments: created → authorized → captured → settled.
    Refunds: created → succeeded/failed.
    Disputes: opened → under_review → won/lost.

    API CONTRACT:
    Backend must expose endpoints for payment intents, refunds, disputes, reconciliation, provider health, and audit logs.
    Vault exposes tokenize, charge-token, rotate-keys.
    Provider-sim supports authorize/capture/refund, webhook emission, and CSV statements.

    SECURITY:
    Header-based RBAC.
    Webhook HMAC validation.
    Vault encryption with key rotation.

    OBSERVABILITY:
    Structured logs.
    Metrics JSONL.
    Correlation IDs.

    IMPLEMENTATION:
    Python 3.12, FastAPI, Uvicorn reload.
    Node 20+, Next.js dev hot reload.
    Atomic file writes with locking.
    Synthetic data generator script.

    REPO STRUCTURE:
    /
      .env
      docker-compose.yml
      README.md
      data/
      frontend/
      backend/api_gateway/
      backend/vault_service/
      backend/provider_sim/
      backend/ledger_jobs/
      backend/shared/

    DOCKER COMPOSE:
    Expose 3026/8026.
    Mount code volumes.
    Mount shared /app/data volume.
    Use root .env.

    README:
    Run instructions.
    Demo scenarios.
    Inspection of files.

    QUALITY BAR:
    Runnable code.
    Production patterns.
    Clear state transitions.
    Error handling.
    Concurrency-safe file writes.

    IMPLEMENT EVERYTHING ABOVE WITHOUT ASKING QUESTIONS.
