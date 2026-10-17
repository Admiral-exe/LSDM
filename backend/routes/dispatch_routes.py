"""
API routes for Workspace 2: Lab Testing & Master Dispatch Entry.
Supports One-Click Dispatch from arrived samples, auto-memory lookup,
split dates, and atomic write-back to MASTER_TEMPLATE.xlsx / Master 2026.xlsx.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import config
from backend.database import get_db_connection, get_config_val, resequence_master_rows
from backend.models import MasterDispatchCreate, MasterDispatchUpdate
from backend.excel_reader import parse_sampno
from backend.excel_writer import AtomicExcelWriter, parse_date_parts
from backend.memory_service import MemoryService

router = APIRouter(prefix="/api/dispatches", tags=["dispatches"])

def get_workspace_dir() -> Path:
    ws_val = get_config_val("workspace_folder_path", str(config.BASE_DIR))
    ws_path = Path(ws_val)
    if not ws_path.exists():
        ws_path = config.BASE_DIR
    return ws_path

def get_master_file_path() -> Path:
    ws_dir = get_workspace_dir()
    master_name = get_config_val("master_file_name", "MASTER_TEMPLATE.xlsx")
    target = ws_dir / master_name
    if not target.exists():
        # Search for any file matching Master*.xlsx
        for f in ws_dir.glob("*.xlsx"):
            if "MASTER" in f.name.upper() and not f.name.startswith("~$") and not f.name.startswith(".tmp_"):
                return f
        # Default back to MASTER_TEMPLATE.xlsx in base dir
        return config.BASE_DIR / "MASTER_TEMPLATE.xlsx"
    return target

@router.get("")
def list_dispatches(
    sheet_name: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Lists dispatch rows from the Master register."""
    query = "SELECT * FROM master_dispatches WHERE 1=1"
    params = []

    if sheet_name:
        query += " AND sheet_name = ?"
        params.append(sheet_name)

    if search:
        s = f"%{search.strip().upper()}%"
        query += """ AND (
            UPPER(sampno) LIKE ? OR 
            UPPER(sampno_raw) LIKE ? OR 
            UPPER(sampname) LIKE ? OR 
            UPPER(batchno) LIKE ? OR 
            UPPER(di_memo_no) LIKE ? OR
            UPPER(mfgname) LIKE ?
        )"""
        params.extend([s, s, s, s, s, s])

    query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM master_dispatches;").fetchone()[0]
        return {
            "total": total,
            "data": [dict(r) for r in rows]
        }

@router.get("/lookup-arrival")
def lookup_arrival(query: str):
    """
    Search arrived samples by Sample No, Memorandum, Batch No, or Name
    to auto-populate the Locked Arrival Plate for one-click dispatch.
    """
    clean_q = query.strip().upper()
    extracted_num = None
    parsed_s = parse_sampno(clean_q)
    if parsed_s:
        extracted_num = parsed_s["sample_no"]

    with get_db_connection() as conn:
        # Search by exact sample_no, memo, batch, or SAMPNO / bracketed SAMPNO
        rows = conn.execute("""
        SELECT m.*, d.id AS existing_dispatch_id, d.sampno AS existing_sampno
        FROM monthly_samples m
        LEFT JOIN master_dispatches d ON m.id = d.monthly_sample_id
        WHERE CAST(m.sample_no AS TEXT) = ?
           OR UPPER(m.memorandum) = ?
           OR UPPER(m.batch_no) = ?
           OR UPPER(m.sample_name) LIKE ?
           OR UPPER(d.sampno) LIKE ?
           OR UPPER(d.sampno_raw) LIKE ?
           OR (? IS NOT NULL AND m.sample_no = ?)
        ORDER BY m.id DESC LIMIT 20;
        """, (clean_q, clean_q, clean_q, f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", extracted_num, extracted_num)).fetchall()

        results = []
        for r in rows:
            item = dict(r)
            # Check if manufacturer details exist in auto-memory
            mfg_info = MemoryService.get_manufacturer(item.get("name_of_mfg", ""))
            item["manufacturer_memory"] = mfg_info

            # Pre-compute target routing and default SAMPNO
            grp = item.get("group_code", "DI")
            target_sheet = config.GROUP_CODE_TO_MASTER_SHEET.get(grp, "DI CMSO UO")
            letter = config.GROUP_CODE_TO_MASTER_LETTER.get(grp, grp[0])
            yy_prefix = item.get("year", 2026) % 100
            s_num = item.get("sample_no", 1)
            suggested_sampno = f"{yy_prefix:02d}{letter}{s_num}"

            item["suggested_sampno"] = suggested_sampno
            item["target_master_sheet"] = target_sheet
            results.append(item)

        return {"results": results}

@router.post("")
def create_dispatch(payload: MasterDispatchCreate):
    """
    Submits a completed testing and dispatch record.
    Saves manufacturer memory, writes to SQLite, updates monthly sample status,
    and atomically writes back to the Master Excel workbook.
    """
    master_path = get_master_file_path()
    if not master_path.exists():
        raise HTTPException(status_code=404, detail=f"Master file {master_path.name} not found.")

    # 1. Auto-save manufacturer details in persistent memory
    if payload.mfgname:
        alias = payload.mfgname.split()[0].upper()
        MemoryService.save_manufacturer({
            "short_name_alias": alias,
            "licence": payload.licence or "",
            "mfgname": payload.mfgname,
            "mfgadd1": payload.mfgadd1 or "",
            "mfgadd2": payload.mfgadd2 or "",
            "mfgadd3": payload.mfgadd3 or "",
            "distcd": payload.distcd or "",
            "statecd": payload.statecd or "",
        })

    # 2. Parse split dates
    r_dd, r_mm, r_yy = parse_date_parts(payload.recdate_iso)
    s_dd, s_mm, s_yy = parse_date_parts(payload.sampdate_iso)
    t_dd, t_mm, t_yy = parse_date_parts(payload.testdate_iso)
    ar_dd, ar_mm, ar_yy = parse_date_parts(payload.ar_report_date_iso)
    m_dd, m_mm, m_yy = parse_date_parts(payload.di_memo_date_iso)

    # 3. Determine next row index in Master sheet
    with get_db_connection() as conn:
        # Check duplicate SAMPNO
        dup = conn.execute("SELECT id FROM master_dispatches WHERE sampno = ?;", (payload.sampno,)).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail=f"SAMPNO '{payload.sampno}' already exists in Master register.")

        row_info = conn.execute("""
        SELECT COALESCE(MAX(excel_row_idx), 2) + 1 AS next_row
        FROM master_dispatches
        WHERE file_name = ? AND sheet_name = ?;
        """, (master_path.name, payload.sheet_name)).fetchone()

        excel_row_idx = row_info["next_row"] if row_info else 3

        cursor = conn.execute("""
        INSERT INTO master_dispatches (
            file_name, sheet_name, excel_row_idx, sampno, sampno_raw,
            year_prefix, group_letter, sample_no,
            recdate_dd, recdate_mm, recdate_yyyy, recdate_iso,
            sampdate_dd, sampdate_mm, sampdate_yyyy, sampdate_iso,
            type, namecd, sender_name, distocd, distoname, placecd, placenm,
            sampname, batchno, licence, mfgname, mfgadd1, mfgadd2, mfgadd3,
            distcd, statecd, testrepo_q, testrepo_quarter, testrepo_no,
            testrepo_yyyy, testrepo_group, testdate_dd, testdate_mm, testdate_yyyy,
            testdate_iso, result, nsq, det1_nsq, fees, ar_report_no,
            ar_report_date_dd, ar_report_date_mm, ar_report_date_yyyy, ar_report_date_iso,
            di_memo_no, di_memo_date_dd, di_memo_date_mm, di_memo_date_yyyy, di_memo_date_iso,
            govt_analyst, extra_fees, monthly_sample_id, sync_status, last_synced_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, 'SYNCED', CURRENT_TIMESTAMP
        );
        """, (
            master_path.name, payload.sheet_name, excel_row_idx, payload.sampno, payload.sampno_raw or payload.sampno,
            payload.year_prefix, payload.group_letter, payload.sample_no,
            r_dd, r_mm, r_yy, payload.recdate_iso,
            s_dd, s_mm, s_yy, payload.sampdate_iso,
            payload.type, payload.namecd, payload.sender_name, payload.distocd, payload.distoname, payload.placecd, payload.placenm,
            payload.sampname, payload.batchno, payload.licence, payload.mfgname, payload.mfgadd1, payload.mfgadd2, payload.mfgadd3,
            payload.distcd, payload.statecd, payload.testrepo_q, payload.testrepo_quarter, payload.testrepo_no,
            payload.testrepo_yyyy, payload.testrepo_group, t_dd, t_mm, t_yy,
            payload.testdate_iso, payload.result, payload.nsq, payload.det1_nsq, str(payload.fees), payload.ar_report_no,
            ar_dd, ar_mm, ar_yy, payload.ar_report_date_iso,
            payload.di_memo_no, m_dd, m_mm, m_yy, payload.di_memo_date_iso,
            payload.govt_analyst, payload.extra_fees, payload.monthly_sample_id
        ))
        new_id = cursor.lastrowid

        # Update linked monthly sample status
        if payload.monthly_sample_id:
            conn.execute("UPDATE monthly_samples SET dispatch_status = 'DISPATCHED' WHERE id = ?;", (payload.monthly_sample_id,))

    # 4. Atomic Write-Back to Master Excel File
    try:
        data_dict = payload.dict()
        data_dict["excel_row_idx"] = excel_row_idx
        AtomicExcelWriter.write_master_row(
            file_path=master_path,
            sheet_name=payload.sheet_name,
            row_idx=excel_row_idx,
            data=data_dict
        )
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE master_dispatches SET sync_status = 'ERROR' WHERE id = ?;", (new_id,))
        raise HTTPException(status_code=500, detail=f"SQLite saved, but Master Excel atomic write failed: {str(e)}")

    return {"status": "success", "id": new_id, "sampno": payload.sampno, "excel_row_idx": excel_row_idx}

@router.put("/{dispatch_id}")
def update_dispatch(dispatch_id: int, payload: MasterDispatchUpdate):
    """Updates an existing Master dispatch row in SQLite and Excel."""
    master_path = get_master_file_path()

    with get_db_connection() as conn:
        existing = conn.execute("SELECT * FROM master_dispatches WHERE id = ?;", (dispatch_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Dispatch record not found.")

        excel_row_idx = existing["excel_row_idx"]
        sheet_name = existing["sheet_name"]

        r_dd, r_mm, r_yy = parse_date_parts(payload.recdate_iso)
        s_dd, s_mm, s_yy = parse_date_parts(payload.sampdate_iso)
        t_dd, t_mm, t_yy = parse_date_parts(payload.testdate_iso)
        ar_dd, ar_mm, ar_yy = parse_date_parts(payload.ar_report_date_iso)
        m_dd, m_mm, m_yy = parse_date_parts(payload.di_memo_date_iso)

        conn.execute("""
        UPDATE master_dispatches SET
            sampname = ?,
            batchno = ?,
            licence = ?,
            mfgname = ?,
            mfgadd1 = ?,
            mfgadd2 = ?,
            mfgadd3 = ?,
            distcd = ?,
            statecd = ?,
            recdate_dd = ?, recdate_mm = ?, recdate_yyyy = ?, recdate_iso = ?,
            sampdate_dd = ?, sampdate_mm = ?, sampdate_yyyy = ?, sampdate_iso = ?,
            testdate_dd = ?, testdate_mm = ?, testdate_yyyy = ?, testdate_iso = ?,
            result = ?,
            nsq = ?,
            det1_nsq = ?,
            fees = ?,
            ar_report_no = ?,
            ar_report_date_dd = ?, ar_report_date_mm = ?, ar_report_date_yyyy = ?, ar_report_date_iso = ?,
            di_memo_no = ?,
            di_memo_date_dd = ?, di_memo_date_mm = ?, di_memo_date_yyyy = ?, di_memo_date_iso = ?,
            govt_analyst = ?,
            extra_fees = ?,
            last_synced_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (
            payload.sampname, payload.batchno, payload.licence, payload.mfgname,
            payload.mfgadd1, payload.mfgadd2, payload.mfgadd3, payload.distcd, payload.statecd,
            r_dd, r_mm, r_yy, payload.recdate_iso,
            s_dd, s_mm, s_yy, payload.sampdate_iso,
            t_dd, t_mm, t_yy, payload.testdate_iso,
            payload.result, payload.nsq, payload.det1_nsq, str(payload.fees), payload.ar_report_no,
            ar_dd, ar_mm, ar_yy, payload.ar_report_date_iso,
            payload.di_memo_no, m_dd, m_mm, m_yy, payload.di_memo_date_iso,
            payload.govt_analyst, payload.extra_fees,
            dispatch_id
        ))

    # Two-Way Atomic Write-Back
    try:
        data_dict = payload.dict()
        data_dict["excel_row_idx"] = excel_row_idx
        AtomicExcelWriter.write_master_row(
            file_path=master_path,
            sheet_name=sheet_name,
            row_idx=excel_row_idx,
            data=data_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Master Excel: {str(e)}")

    return {"status": "success"}

@router.delete("/{dispatch_id}")
def delete_dispatch(dispatch_id: int):
    """
    Deletes a Master dispatch row, shifts subsequent Excel rows up by 1,
    and updates SQLite row indices.
    """
    master_path = get_master_file_path()

    with get_db_connection() as conn:
        existing = conn.execute("SELECT * FROM master_dispatches WHERE id = ?;", (dispatch_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Dispatch record not found.")

        file_name = existing["file_name"]
        sheet_name = existing["sheet_name"]
        excel_row_idx = existing["excel_row_idx"]
        monthly_id = existing["monthly_sample_id"]

        # Reset monthly sample status to PENDING
        if monthly_id:
            conn.execute("UPDATE monthly_samples SET dispatch_status = 'PENDING' WHERE id = ?;", (monthly_id,))

        conn.execute("DELETE FROM master_dispatches WHERE id = ?;", (dispatch_id,))

    # Delete in Excel
    if master_path.exists():
        try:
            AtomicExcelWriter.delete_excel_row(
                file_path=master_path,
                sheet_name=sheet_name,
                row_idx=excel_row_idx,
                is_monthly=False
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete row in Master Excel: {str(e)}")

    # Resequence subsequent rows in SQLite
    resequence_master_rows(file_name, sheet_name, excel_row_idx)

    return {"status": "success"}
