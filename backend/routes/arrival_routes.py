"""
API routes for Workspace 1: Monthly Arrival Register.
Supports CRUD, auto-increment sample numbering, atomic Excel sync, and New Month File generation.
"""
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import config
from backend.database import get_db_connection, get_config_val, resequence_monthly_rows
from backend.models import MonthlySampleCreate, MonthlySampleUpdate, NewMonthFileRequest
from backend.excel_writer import AtomicExcelWriter
from backend.excel_reader import ExcelReader

router = APIRouter(prefix="/api/arrivals", tags=["arrivals"])

def get_workspace_dir() -> Path:
    ws_val = get_config_val("workspace_folder_path", str(config.BASE_DIR))
    ws_path = Path(ws_val)
    if not ws_path.exists():
        ws_path = config.BASE_DIR
    return ws_path

@router.get("/files")
def list_arrival_files():
    """Lists all detected monthly files in the active workspace."""
    ws_dir = get_workspace_dir()
    files = []
    with get_db_connection() as conn:
        rows = conn.execute("SELECT DISTINCT file_name FROM monthly_samples ORDER BY file_name ASC;").fetchall()
        for r in rows:
            files.append(r["file_name"])

    # Also list matching files on disk even if 0 rows in DB yet
    for f in ws_dir.glob("*.xlsx"):
        if f.name.startswith("~$") or f.name.startswith(".tmp_") or "MASTER" in f.name.upper():
            continue
        if f.name not in files:
            files.append(f.name)

    return {"files": files}

@router.get("")
def list_arrivals(
    file_name: Optional[str] = None,
    group_code: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Retrieves arrival rows with multi-field filtering."""
    query = "SELECT * FROM monthly_samples WHERE 1=1"
    params = []

    if file_name and file_name != "ALL":
        query += " AND file_name = ?"
        params.append(file_name)

    if group_code:
        query += " AND group_code = ?"
        params.append(group_code)

    if search:
        s = f"%{search.strip().upper()}%"
        query += """ AND (
            UPPER(sample_name) LIKE ? OR 
            UPPER(batch_no) LIKE ? OR 
            UPPER(memorandum) LIKE ? OR 
            UPPER(name_of_mfg) LIKE ? OR
            CAST(sample_no AS TEXT) LIKE ?
        )"""
        params.extend([s, s, s, s, s])

    query += " ORDER BY sample_no ASC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM monthly_samples;").fetchone()[0]
        return {
            "total": total,
            "data": [dict(r) for r in rows]
        }

@router.get("/next-sample-no")
def get_next_sample_no(year: int, group_code: str):
    """Calculates the next sequential sample number across the entire year for a group."""
    with get_db_connection() as conn:
        row = conn.execute("""
        SELECT COALESCE(MAX(sample_no), 0) + 1 AS next_no
        FROM monthly_samples
        WHERE year = ? AND group_code = ?;
        """, (year, group_code)).fetchone()
        return {"next_sample_no": row["next_no"] if row else 1}

@router.post("")
def create_arrival(payload: MonthlySampleCreate):
    """
    Creates a new sample arrival record.
    Commits immediately to SQLite and writes back atomically to the corresponding .xlsx file.
    """
    ws_dir = get_workspace_dir()
    target_file = ws_dir / payload.file_name

    if not target_file.exists():
        # Fall back to template cloning if file does not exist yet
        template_file = ws_dir / "APRIL_TEMPLATE.xlsx"
        if not template_file.exists():
            template_file = config.BASE_DIR / "APRIL_TEMPLATE.xlsx"
        if template_file.exists():
            shutil.copy2(template_file, target_file)
        else:
            raise HTTPException(status_code=404, detail=f"Target file {payload.file_name} not found and template missing.")

    # Calculate next serial no and excel row index
    with get_db_connection() as conn:
        # Check duplicate sample_no in same year and group
        dup = conn.execute("""
        SELECT id FROM monthly_samples 
        WHERE year = ? AND group_code = ? AND sample_no = ?;
        """, (payload.year, payload.group_code, payload.sample_no)).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail=f"Sample No {payload.sample_no} already exists for group {payload.group_code} in year {payload.year}.")

        sr_row = conn.execute("""
        SELECT COALESCE(MAX(sr_no), 0) + 1 AS next_sr,
               COALESCE(MAX(excel_row_idx), 1) + 1 AS next_row
        FROM monthly_samples
        WHERE file_name = ? AND sheet_name = ?;
        """, (payload.file_name, payload.sheet_name)).fetchone()

        sr_no = payload.sr_no or (sr_row["next_sr"] if sr_row else 1)
        excel_row_idx = sr_row["next_row"] if sr_row else 2

        # Inspector and city splitting
        inspector = payload.inspector_name or ""
        city = payload.city_district or ""
        di_name_city = payload.di_name_city or (f"{inspector} ({city})" if city else inspector)

        cursor = conn.execute("""
        INSERT INTO monthly_samples (
            file_name, month_name, year, sheet_name, group_code, excel_row_idx,
            sr_no, receive_date, sample_no, division, tp_proce, catgo_name,
            catego_no, g_og, sample_name, batch_no, exp_date, name_of_mfg,
            di_name_city, inspector_name, city_district, memorandum,
            distributed_to, distribution_date, weightage, sync_status, last_synced_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, 'SYNCED', CURRENT_TIMESTAMP
        );
        """, (
            payload.file_name, payload.month_name, payload.year, payload.sheet_name, payload.group_code, excel_row_idx,
            sr_no, payload.receive_date, payload.sample_no, payload.division, payload.tp_proce, payload.catgo_name,
            payload.catego_no, payload.g_og, payload.sample_name, payload.batch_no, payload.exp_date, payload.name_of_mfg,
            di_name_city, inspector, city, payload.memorandum,
            payload.distributed_to, payload.distribution_date, payload.weightage
        ))
        new_id = cursor.lastrowid

    # Two-Way Atomic Write-Back to Excel
    try:
        row_dict = payload.dict()
        row_dict["sr_no"] = sr_no
        row_dict["excel_row_idx"] = excel_row_idx
        row_dict["di_name_city"] = di_name_city
        AtomicExcelWriter.write_monthly_row(
            file_path=target_file,
            sheet_name=payload.sheet_name,
            row_idx=excel_row_idx,
            data=row_dict
        )
    except Exception as e:
        # Roll back SQLite or flag error
        with get_db_connection() as conn:
            conn.execute("UPDATE monthly_samples SET sync_status = 'ERROR' WHERE id = ?;", (new_id,))
        raise HTTPException(status_code=500, detail=f"SQLite saved, but Excel atomic write failed: {str(e)}")

    return {"status": "success", "id": new_id, "sr_no": sr_no, "excel_row_idx": excel_row_idx}

@router.put("/{sample_id}")
def update_arrival(sample_id: int, payload: MonthlySampleUpdate):
    """Updates an existing arrival row in SQLite and Excel."""
    ws_dir = get_workspace_dir()
    target_file = ws_dir / payload.file_name

    with get_db_connection() as conn:
        existing = conn.execute("SELECT * FROM monthly_samples WHERE id = ?;", (sample_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Arrival sample not found.")

        excel_row_idx = existing["excel_row_idx"]
        sr_no = existing["sr_no"]

        inspector = payload.inspector_name or ""
        city = payload.city_district or ""
        di_name_city = payload.di_name_city or (f"{inspector} ({city})" if city else inspector)

        conn.execute("""
        UPDATE monthly_samples SET
            receive_date = ?,
            sample_name = ?,
            batch_no = ?,
            exp_date = ?,
            name_of_mfg = ?,
            di_name_city = ?,
            inspector_name = ?,
            city_district = ?,
            memorandum = ?,
            division = ?,
            tp_proce = ?,
            catgo_name = ?,
            catego_no = ?,
            g_og = ?,
            distributed_to = ?,
            distribution_date = ?,
            weightage = ?,
            last_synced_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (
            payload.receive_date, payload.sample_name, payload.batch_no, payload.exp_date,
            payload.name_of_mfg, di_name_city, inspector, city, payload.memorandum,
            payload.division, payload.tp_proce, payload.catgo_name, payload.catego_no, payload.g_og,
            payload.distributed_to, payload.distribution_date, payload.weightage,
            sample_id
        ))

    # Two-Way Atomic Write-Back
    try:
        row_dict = payload.dict()
        row_dict["sr_no"] = sr_no
        row_dict["di_name_city"] = di_name_city
        AtomicExcelWriter.write_monthly_row(
            file_path=target_file,
            sheet_name=payload.sheet_name,
            row_idx=excel_row_idx,
            data=row_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Excel: {str(e)}")

    return {"status": "success"}

@router.delete("/{sample_id}")
def delete_arrival(sample_id: int):
    """
    Deletes an arrival row, deletes from Excel, shifts subsequent rows up by 1,
    and updates SQLite row indices so SQLite and Excel never desynchronize.
    """
    ws_dir = get_workspace_dir()

    with get_db_connection() as conn:
        existing = conn.execute("SELECT * FROM monthly_samples WHERE id = ?;", (sample_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Arrival sample not found.")

        file_name = existing["file_name"]
        sheet_name = existing["sheet_name"]
        excel_row_idx = existing["excel_row_idx"]

        # Check if linked to Master
        linked = conn.execute("SELECT id FROM master_dispatches WHERE monthly_sample_id = ?;", (sample_id,)).fetchall()
        if linked:
            # Unlink master records
            conn.execute("UPDATE master_dispatches SET monthly_sample_id = NULL WHERE monthly_sample_id = ?;", (sample_id,))

        # Delete row in SQLite
        conn.execute("DELETE FROM monthly_samples WHERE id = ?;", (sample_id,))

    # Delete row in Excel and renumber SR. NO
    target_file = ws_dir / file_name
    if target_file.exists():
        try:
            AtomicExcelWriter.delete_excel_row(
                file_path=target_file,
                sheet_name=sheet_name,
                row_idx=excel_row_idx,
                is_monthly=True
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete row in Excel: {str(e)}")

    # Shift subsequent rows in SQLite
    resequence_monthly_rows(file_name, sheet_name, excel_row_idx)

    return {"status": "success", "unlinked_master_count": len(linked)}

@router.post("/new-month-file")
def create_new_month_file(payload: NewMonthFileRequest):
    """
    Clones the clean 5-tab template structure of APRIL_TEMPLATE.xlsx to <MONTH> <YEAR>.xlsx,
    registers it in SQLite, and computes the continuing baseline sample numbers.
    """
    ws_dir = get_workspace_dir()
    new_filename = f"{payload.month_name.upper()} {payload.year}.xlsx"
    target_path = ws_dir / new_filename

    if target_path.exists():
        raise HTTPException(status_code=400, detail=f"File '{new_filename}' already exists in workspace.")

    # Locate source template
    src_template = ws_dir / "APRIL_TEMPLATE.xlsx"
    if not src_template.exists():
        src_template = config.BASE_DIR / "APRIL_TEMPLATE.xlsx"
    if not src_template.exists():
        raise HTTPException(status_code=404, detail="Source template APRIL_TEMPLATE.xlsx not found.")

    try:
        shutil.copy2(src_template, target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy template: {str(e)}")

    # Calculate starting numbers for each group
    starting_numbers = {}
    with get_db_connection() as conn:
        for grp in config.SAMPLE_GROUPS:
            row = conn.execute("""
            SELECT COALESCE(MAX(sample_no), 0) + 1 AS start_no
            FROM monthly_samples
            WHERE year = ? AND group_code = ?;
            """, (payload.year, grp)).fetchone()
            starting_numbers[grp] = row["start_no"] if row else 1

    return {
        "status": "success",
        "file_name": new_filename,
        "starting_sample_numbers": starting_numbers
    }
