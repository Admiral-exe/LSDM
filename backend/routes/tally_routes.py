"""
API routes for Workspace 3: Multi-File Tally & Reconciliation Engine.
Provides instant summary metrics, side-by-side reconciliation diffs, and auto-repair actions.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.tally_engine import TallyEngine
from backend.database import get_db_connection

router = APIRouter(prefix="/api/tally", tags=["tally"])

class LinkRepairRequest(BaseModel):
    monthly_id: int
    master_id: int

class FieldSyncRequest(BaseModel):
    monthly_id: int
    master_id: int
    field_name: str # e.g. 'batch_no' or 'memorandum'
    source: str     # 'monthly' or 'master'

@router.get("/summary")
def get_tally_summary():
    """Returns high-level tally metrics across all files in <100ms."""
    return TallyEngine.get_summary_metrics()

@router.get("/details")
def get_tally_details(filter_type: str = Query("ALL", pattern="^(ALL|PENDING|TALLIED|ORPHAN|DISCREPANCY)$")):
    """Returns detailed reconciliation rows with hardware LED states and mismatch details."""
    details = TallyEngine.get_reconciliation_details(filter_type)
    return {"count": len(details), "data": details}

@router.post("/repair-link")
def repair_link(payload: LinkRepairRequest):
    """Manually links an orphan master record to a monthly sample."""
    with get_db_connection() as conn:
        conn.execute("""
        UPDATE master_dispatches 
        SET monthly_sample_id = ?, sync_status = 'DIRTY'
        WHERE id = ?;
        """, (payload.monthly_id, payload.master_id))

        conn.execute("""
        UPDATE monthly_samples 
        SET dispatch_status = 'DISPATCHED'
        WHERE id = ?;
        """, (payload.monthly_id,))

    return {"status": "success", "message": "Records linked successfully."}

@router.post("/repair-sync-field")
def repair_sync_field(payload: FieldSyncRequest):
    """Synchronizes a mismatched field between Monthly and Master records."""
    with get_db_connection() as conn:
        m_row = conn.execute("SELECT * FROM monthly_samples WHERE id = ?;", (payload.monthly_id,)).fetchone()
        d_row = conn.execute("SELECT * FROM master_dispatches WHERE id = ?;", (payload.master_id,)).fetchone()

        if not m_row or not d_row:
            raise HTTPException(status_code=404, detail="One or both records not found.")

        if payload.field_name == "batch_no":
            if payload.source == "monthly":
                val = m_row["batch_no"]
                conn.execute("UPDATE master_dispatches SET batchno = ?, sync_status = 'DIRTY' WHERE id = ?;", (val, payload.master_id))
            else:
                val = d_row["batchno"]
                conn.execute("UPDATE monthly_samples SET batch_no = ?, sync_status = 'DIRTY' WHERE id = ?;", (val, payload.monthly_id))
        elif payload.field_name == "memorandum":
            if payload.source == "monthly":
                val = m_row["memorandum"]
                conn.execute("UPDATE master_dispatches SET di_memo_no = ?, sync_status = 'DIRTY' WHERE id = ?;", (val, payload.master_id))
            else:
                val = d_row["di_memo_no"]
                conn.execute("UPDATE monthly_samples SET memorandum = ?, sync_status = 'DIRTY' WHERE id = ?;", (val, payload.monthly_id))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported field sync: {payload.field_name}")

    return {"status": "success", "message": f"Field '{payload.field_name}' synchronized from {payload.source}."}
