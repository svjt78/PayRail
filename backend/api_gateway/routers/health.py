"""Health and provider status endpoints."""

import os
import logging

from fastapi import APIRouter, Query

from shared.file_store import FileStore
from services.circuit_breaker import CircuitBreaker

logger = logging.getLogger("payrail.health")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
PROVIDERS = ["providerA", "providerB"]


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "api-gateway"}


@router.get("/providers/health")
async def provider_health():
    providers = []
    for pid in PROVIDERS:
        cb = CircuitBreaker(pid)
        state = cb.get_state()
        providers.append({
            "provider_id": pid,
            "circuit_state": state.get("circuit_state", "closed"),
            "failure_count": state.get("failure_count", 0),
            "success_count": state.get("success_count", 0),
            "total_requests": state.get("total_requests", 0),
            "last_failure_at": state.get("last_failure_at"),
            "last_success_at": state.get("last_success_at"),
            "can_execute": cb.can_execute(),
        })
    return {"providers": providers}


@router.get("/metrics")
async def get_metrics(limit: int = Query(100, le=1000)):
    metrics_path = os.path.join(DATA_DIR, "metrics", "service_metrics.jsonl")
    entries = FileStore.read_jsonl(metrics_path)
    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}


@router.get("/ledger/{ref_id}")
async def get_ledger_entries(ref_id: str):
    from services.ledger import LedgerService
    svc = LedgerService()
    entries = svc.get_entries_for_ref(ref_id)
    return {"ref_id": ref_id, "entries": entries, "total": len(entries)}
