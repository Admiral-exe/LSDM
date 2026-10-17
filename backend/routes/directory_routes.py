"""
API routes for Workspace 4: Master Directories, Lookups, and Workspace Configuration.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import config
from backend.database import get_db_connection, get_config_val, set_config_val
from backend.models import ManufacturerModel, InspectorModel, WorkspaceConfigRequest
from backend.memory_service import MemoryService
from backend.excel_reader import ExcelReader

router = APIRouter(prefix="/api/directories", tags=["directories"])

@router.get("/manufacturers")
def list_manufacturers(search: Optional[str] = None):
    """Lists saved manufacturers with auto-complete search."""
    if search:
        return {"data": MemoryService.search_manufacturers(search)}
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM manufacturers ORDER BY short_name_alias ASC;").fetchall()
        return {"data": [dict(r) for r in rows]}

@router.post("/manufacturers")
def save_manufacturer(payload: ManufacturerModel):
    """Saves or updates a 7-field manufacturer profile in persistent memory."""
    saved = MemoryService.save_manufacturer(payload.dict())
    return {"status": "success", "data": saved}

@router.delete("/manufacturers/{mfg_id}")
def delete_manufacturer(mfg_id: int):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM manufacturers WHERE id = ?;", (mfg_id,))
    return {"status": "success"}

@router.get("/inspectors")
def list_inspectors(search: Optional[str] = None):
    """Lists saved inspectors."""
    if search:
        return {"data": MemoryService.search_inspectors(search)}
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM inspectors ORDER BY inspector_name ASC;").fetchall()
        return {"data": [dict(r) for r in rows]}

@router.post("/inspectors")
def save_inspector(payload: InspectorModel):
    """Saves an inspector with default district."""
    saved = MemoryService.save_inspector(
        payload.inspector_name,
        payload.default_district_name or "",
        payload.default_district_code
    )
    return {"status": "success", "data": saved}

@router.get("/districts")
def list_districts():
    """Returns Gujarat standard district code lookup table."""
    return {"data": MemoryService.get_all_districts()}

@router.get("/config")
def get_workspace_config():
    """Retrieves current workspace settings."""
    ws_dir = get_config_val("workspace_folder_path", str(config.BASE_DIR))
    year = get_config_val("active_year", "2026")
    master_name = get_config_val("master_file_name", "MASTER_TEMPLATE.xlsx")
    return {
        "workspace_folder_path": ws_dir,
        "active_year": int(year),
        "master_file_name": master_name,
    }

@router.post("/config")
def update_workspace_config(payload: WorkspaceConfigRequest):
    """Updates active workspace directory and runs an ingestion scan."""
    path = Path(payload.workspace_folder_path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory path '{payload.workspace_folder_path}' does not exist.")

    set_config_val("workspace_folder_path", str(path.resolve()))
    scan_result = ExcelReader.full_scan_workspace(path)
    return {
        "status": "success",
        "workspace_folder_path": str(path.resolve()),
        "scan_result": scan_result
    }

@router.post("/rescan")
def force_rescan():
    """Forces an immediate full re-scan of the active workspace folder into SQLite."""
    ws_dir_str = get_config_val("workspace_folder_path", str(config.BASE_DIR))
    ws_dir = Path(ws_dir_str)
    if not ws_dir.exists():
        ws_dir = config.BASE_DIR

    scan_result = ExcelReader.full_scan_workspace(ws_dir)
    return {
        "status": "success",
        "folder": str(ws_dir),
        "result": scan_result
    }

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50):
    """Retrieves recent atomic sync operations and backup records."""
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM sync_audit_log ORDER BY id DESC LIMIT ?;", (limit,)).fetchall()
        return {"data": [dict(r) for r in rows]}
