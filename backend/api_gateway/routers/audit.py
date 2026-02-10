"""Audit router - audit trails and export."""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Query

from shared.file_store import FileStore
from services.ledger import LedgerService

logger = logging.getLogger("payrail.audit")
router = APIRouter()

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
ledger = LedgerService()


@router.get("/payments")
async def audit_payments(
    ref_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    if ref_id:
        entries = ledger.get_entries_for_ref(ref_id)
        return {"entries": entries, "total": len(entries)}

    entries, total = ledger.get_all_entries("payment", limit, offset)
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}


@router.get("/refunds")
async def audit_refunds(
    ref_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    if ref_id:
        entries = ledger.get_entries_for_ref(ref_id)
        return {"entries": entries, "total": len(entries)}

    entries, total = ledger.get_all_entries("refund", limit, offset)
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}


@router.get("/disputes")
async def audit_disputes(
    ref_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    if ref_id:
        entries = ledger.get_entries_for_ref(ref_id)
        return {"entries": entries, "total": len(entries)}

    entries, total = ledger.get_all_entries("dispute", limit, offset)
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}


@router.get("/vault-access")
async def audit_vault_access(limit: int = Query(100, le=500)):
    access_log_path = os.path.join(DATA_DIR, "vault", "access_log.jsonl")
    entries = FileStore.read_jsonl(access_log_path)
    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}


@router.get("/export")
async def export_audit(entity_type: str = Query("payment")):
    entries, total = ledger.get_all_entries(entity_type, limit=10000, offset=0)
    return {
        "entity_type": entity_type,
        "entries": entries,
        "total": total,
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.get("/reconciliation")
async def get_reconciliation_reports():
    recon_dir = os.path.join(DATA_DIR, "reconciliation")
    if not os.path.exists(recon_dir):
        return {"reports": []}

    reports = []
    import glob
    for path in sorted(glob.glob(os.path.join(recon_dir, "*.json")), reverse=True):
        data = FileStore.read_json(path)
        reports.append(data)
    return {"reports": reports}


@router.get("/settlements")
async def get_settlements():
    settlement_dir = os.path.join(DATA_DIR, "settlement")
    if not os.path.exists(settlement_dir):
        return {"settlements": []}

    settlements = []
    import glob
    for path in sorted(glob.glob(os.path.join(settlement_dir, "*.csv")), reverse=True):
        rows = FileStore.read_csv(path)
        filename = os.path.basename(path)
        total_amount = sum(int(r.get("amount", 0)) for r in rows)
        settlements.append({
            "file": filename,
            "rows": len(rows),
            "total_amount": total_amount,
            "data": rows,
        })
    return {"settlements": settlements}
