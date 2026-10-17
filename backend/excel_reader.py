"""
Excel ingestion engine.
Reads Monthly Arrival and Master Dispatch .xlsx files into SQLite,
normalizing header variations, the ESIS column shift, and legacy SAMPNO typos.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import openpyxl

import config
from backend.database import get_db_connection, log_audit

SAMPNO_RAW_REGEX = re.compile(r"^(\d{2})([A-Z]+)(\d+)(?:\[(.*)\])?$")
INSPECTOR_REGEX = re.compile(r"^(.*?)\s*\((.*?)\)$")

def clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()

def clean_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        # Handle string floats like '1481.0'
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None

def parse_sampno(raw_sampno: str) -> Optional[Dict[str, Any]]:
    """
    Parses and normalizes SAMPNO strings with typo correction.
    Example: '26DO729[10/IBC]' -> year=2026, group_letter='D', group_code='DI', sample_no=729
             '26UO1484'        -> year=2026, group_letter='UO', group_code='UO', sample_no=1484
    """
    if not raw_sampno:
        return None
    clean = str(raw_sampno).strip().upper()
    match = SAMPNO_RAW_REGEX.match(clean)
    if not match:
        return None

    yy_str, group_token, num_str, bracket_suffix = match.groups()
    year = 2000 + int(yy_str)

    # Legacy Typo Correction: 'DO' -> 'D' + '0', 'CO' -> 'C' + '0', 'PO' -> 'P' + '0', 'EO' -> 'E' + '0'
    # BUT 'UO' is the valid group code for U.O.
    if group_token in ("DO", "CO", "PO", "EO"):
        prefix = group_token[0]
        group_letter = prefix
        sample_num = int("0" + num_str)
    else:
        group_letter = group_token
        sample_num = int(num_str)

    group_map = {
        "D": "DI",
        "DI": "DI",
        "C": "CMSO",
        "CMSO": "CMSO",
        "P": "PDT",
        "PDT": "PDT",
        "U": "UO",
        "UO": "UO",
        "E": "ESIS",
        "ESIS": "ESIS",
    }
    canonical_group = group_map.get(group_letter, group_letter)
    standard_sampno = f"{yy_str}{group_letter}{sample_num}"

    return {
        "sampno": standard_sampno,
        "sampno_raw": clean,
        "year": year,
        "year_prefix": int(yy_str),
        "group_letter": group_letter,
        "group_code": canonical_group,
        "sample_no": sample_num,
        "bracket_suffix": bracket_suffix or "",
    }

def parse_inspector_and_city(raw_text: str) -> tuple[str, str]:
    """Splits 'ABC (JAMNAGAR)' into ('ABC', 'JAMNAGAR')."""
    if not raw_text:
        return "", ""
    clean = clean_str(raw_text)
    match = INSPECTOR_REGEX.match(clean)
    if match:
        return match.group(1).strip(), match.group(2).strip().upper()
    return clean, ""

class ExcelReader:
    @classmethod
    def read_monthly_file(cls, file_path: Path | str) -> int:
        """
        Reads a Monthly arrival file and ingests all rows into monthly_samples.
        Returns count of rows ingested.
        """
        path = Path(file_path)
        if not path.exists():
            return 0

        # Infer month and year from filename (e.g. 'APRIL 2026.xlsx' or 'APRIL_TEMPLATE.xlsx')
        stem = path.stem.upper()
        month_name = "APRIL"
        for m in config.MONTH_NAMES:
            if m in stem:
                month_name = m
                break

        year = 2026
        year_match = re.search(r"\b(20\d\d)\b", stem)
        if year_match:
            year = int(year_match.group(1))

        wb = openpyxl.load_workbook(path, data_only=True)
        total_ingested = 0

        with get_db_connection() as conn:
            for sname in wb.sheetnames:
                if sname not in config.TAB_NAME_TO_GROUP_CODE:
                    continue
                group_code = config.TAB_NAME_TO_GROUP_CODE[sname]
                ws = wb[sname]
                is_esis = (sname == "ESIS")
                col_offset = 0 if not is_esis else -1

                for r in range(2, ws.max_row + 1):
                    # Check if row is completely empty
                    row_vals = [ws.cell(r, c).value for c in range(1, min(ws.max_column + 1, 20))]
                    if not any(v is not None and str(v).strip() != "" for v in row_vals):
                        continue

                    sr_no = clean_int(ws.cell(r, 2 + col_offset).value) or (r - 1)
                    rec_date = clean_str(ws.cell(r, 3 + col_offset).value)
                    sample_no = clean_int(ws.cell(r, 4 + col_offset).value)
                    if sample_no is None:
                        # Skip header or corrupt row missing sample number
                        continue

                    division = clean_str(ws.cell(r, 5 + col_offset).value)
                    tp_proce = clean_str(ws.cell(r, 6 + col_offset).value)
                    catgo_name = clean_str(ws.cell(r, 7 + col_offset).value)
                    catego_no = clean_str(ws.cell(r, 8 + col_offset).value)
                    g_og = clean_str(ws.cell(r, 9 + col_offset).value)
                    sample_name = clean_str(ws.cell(r, 10 + col_offset).value)
                    batch_no = clean_str(ws.cell(r, 11 + col_offset).value)
                    exp_date = clean_str(ws.cell(r, 12 + col_offset).value)
                    name_of_mfg = clean_str(ws.cell(r, 13 + col_offset).value)
                    di_name_city = clean_str(ws.cell(r, 14 + col_offset).value)
                    memorandum = clean_str(ws.cell(r, 15 + col_offset).value)
                    dist_to = clean_str(ws.cell(r, 16 + col_offset).value)
                    dist_date = clean_str(ws.cell(r, 17 + col_offset).value)
                    weightage = clean_str(ws.cell(r, 18 + col_offset).value)

                    inspector_name, city_district = parse_inspector_and_city(di_name_city)

                    # Insert or update into SQLite
                    conn.execute("""
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
                    )
                    ON CONFLICT(year, group_code, sample_no) DO UPDATE SET
                        file_name = excluded.file_name,
                        excel_row_idx = excluded.excel_row_idx,
                        sr_no = excluded.sr_no,
                        receive_date = excluded.receive_date,
                        sample_name = excluded.sample_name,
                        batch_no = excluded.batch_no,
                        exp_date = excluded.exp_date,
                        name_of_mfg = excluded.name_of_mfg,
                        di_name_city = excluded.di_name_city,
                        inspector_name = excluded.inspector_name,
                        city_district = excluded.city_district,
                        memorandum = excluded.memorandum,
                        sync_status = 'SYNCED',
                        last_synced_at = CURRENT_TIMESTAMP;
                    """, (
                        path.name, month_name, year, sname, group_code, r,
                        sr_no, rec_date, sample_no, division, tp_proce, catgo_name,
                        catego_no, g_og, sample_name, batch_no, exp_date, name_of_mfg,
                        di_name_city, inspector_name, city_district, memorandum,
                        dist_to, dist_date, weightage
                    ))

                    # Seed inspector if not present
                    if inspector_name:
                        conn.execute("""
                        INSERT OR IGNORE INTO inspectors (inspector_name, default_district_name)
                        VALUES (?, ?);
                        """, (inspector_name, city_district))

                    total_ingested += 1

        wb.close()
        log_audit("INGEST_MONTHLY", path.name, details=f"Ingested {total_ingested} rows.")
        return total_ingested

    @classmethod
    def read_master_file(cls, file_path: Path | str) -> int:
        """
        Reads a Master Testing & Dispatch file and ingests into master_dispatches.
        Normalizes split dates, TESTREPO blocks, and links with monthly_samples.
        """
        path = Path(file_path)
        if not path.exists():
            return 0

        wb = openpyxl.load_workbook(path, data_only=True)
        total_ingested = 0

        with get_db_connection() as conn:
            for sname in ["DI CMSO UO", "PDT"]:
                if sname not in wb.sheetnames:
                    continue
                ws = wb[sname]

                # Data rows start at Row 3
                for r in range(3, ws.max_row + 1):
                    raw_sampno = clean_str(ws.cell(r, 1).value)
                    if not raw_sampno:
                        continue

                    parsed_s = parse_sampno(raw_sampno)
                    if not parsed_s:
                        continue

                    # Dates
                    r_dd = clean_int(ws.cell(r, 2).value)
                    r_mm = clean_int(ws.cell(r, 3).value)
                    r_yy = clean_int(ws.cell(r, 4).value)
                    r_iso = f"{r_yy:04d}-{r_mm:02d}-{r_dd:02d}" if (r_yy and r_mm and r_dd) else ""

                    s_dd = clean_int(ws.cell(r, 5).value)
                    s_mm = clean_int(ws.cell(r, 6).value)
                    s_yy = clean_int(ws.cell(r, 7).value)
                    s_iso = f"{s_yy:04d}-{s_mm:02d}-{s_dd:02d}" if (s_yy and s_mm and s_dd) else ""

                    samp_type = clean_str(ws.cell(r, 8).value)
                    namecd = clean_str(ws.cell(r, 9).value)
                    sender_name = clean_str(ws.cell(r, 10).value)
                    distocd = clean_int(ws.cell(r, 11).value)
                    distoname = clean_str(ws.cell(r, 12).value)
                    placecd = clean_str(ws.cell(r, 13).value)
                    placenm = clean_str(ws.cell(r, 14).value)
                    sampname = clean_str(ws.cell(r, 15).value)
                    batchno = clean_str(ws.cell(r, 16).value)
                    licence = clean_str(ws.cell(r, 17).value)

                    # Cols 19-24: Manufacturer
                    mfgname = clean_str(ws.cell(r, 19).value)
                    mfgadd1 = clean_str(ws.cell(r, 20).value)
                    mfgadd2 = clean_str(ws.cell(r, 21).value)
                    mfgadd3 = clean_str(ws.cell(r, 22).value)
                    distcd = clean_str(ws.cell(r, 23).value)
                    statecd = clean_str(ws.cell(r, 24).value)

                    # Cols 25-29: TESTREPO
                    q_val = clean_str(ws.cell(r, 25).value) or "Q"
                    quarter = clean_int(ws.cell(r, 26).value) or 1
                    report_no = clean_str(ws.cell(r, 27).value)
                    repo_year = clean_int(ws.cell(r, 28).value) or parsed_s["year"]
                    repo_group = clean_str(ws.cell(r, 29).value) or parsed_s["group_code"]

                    # Cols 30-32: TESTDATE
                    t_dd = clean_int(ws.cell(r, 30).value)
                    t_mm = clean_int(ws.cell(r, 31).value)
                    t_yy = clean_int(ws.cell(r, 32).value)
                    t_iso = f"{t_yy:04d}-{t_mm:02d}-{t_dd:02d}" if (t_yy and t_mm and t_dd) else ""

                    result_code = clean_int(ws.cell(r, 33).value) or 1
                    nsq = clean_str(ws.cell(r, 34).value)
                    det1_nsq = clean_str(ws.cell(r, 35).value)
                    fees = clean_str(ws.cell(r, 36).value) or "NIL"
                    ar_report_no = clean_str(ws.cell(r, 37).value)

                    # Cols 38-40: AR REPORT DATE
                    ar_dd = clean_int(ws.cell(r, 38).value)
                    ar_mm = clean_int(ws.cell(r, 39).value)
                    ar_yy = clean_int(ws.cell(r, 40).value)
                    ar_iso = f"{ar_yy:04d}-{ar_mm:02d}-{ar_dd:02d}" if (ar_yy and ar_mm and ar_dd) else ""

                    di_memo_no = clean_str(ws.cell(r, 41).value)

                    # Cols 42-44: DI MEMO DATE
                    m_dd = clean_int(ws.cell(r, 42).value)
                    m_mm = clean_int(ws.cell(r, 43).value)
                    m_yy = clean_int(ws.cell(r, 44).value)
                    m_iso = f"{m_yy:04d}-{m_mm:02d}-{m_dd:02d}" if (m_yy and m_mm and m_dd) else ""

                    govt_analyst = clean_str(ws.cell(r, 45).value)
                    extra_fees = clean_str(ws.cell(r, 46).value) if sname == "PDT" else ""

                    # Link with monthly_samples
                    monthly_row = conn.execute("""
                    SELECT id FROM monthly_samples 
                    WHERE year = ? AND group_code = ? AND sample_no = ?;
                    """, (parsed_s["year"], parsed_s["group_code"], parsed_s["sample_no"])).fetchone()

                    monthly_id = monthly_row["id"] if monthly_row else None

                    conn.execute("""
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
                    )
                    ON CONFLICT(sampno) DO UPDATE SET
                        file_name = excluded.file_name,
                        excel_row_idx = excluded.excel_row_idx,
                        sampname = excluded.sampname,
                        batchno = excluded.batchno,
                        licence = excluded.licence,
                        mfgname = excluded.mfgname,
                        result = excluded.result,
                        fees = excluded.fees,
                        monthly_sample_id = excluded.monthly_sample_id,
                        sync_status = 'SYNCED',
                        last_synced_at = CURRENT_TIMESTAMP;
                    """, (
                        path.name, sname, r, parsed_s["sampno"], parsed_s["sampno_raw"],
                        parsed_s["year_prefix"], parsed_s["group_letter"], parsed_s["sample_no"],
                        r_dd, r_mm, r_yy, r_iso,
                        s_dd, s_mm, s_yy, s_iso,
                        samp_type, namecd, sender_name, distocd, distoname, placecd, placenm,
                        sampname, batchno, licence, mfgname, mfgadd1, mfgadd2, mfgadd3,
                        distcd, statecd, q_val, quarter, report_no,
                        repo_year, repo_group, t_dd, t_mm, t_yy,
                        t_iso, result_code, nsq, det1_nsq, fees, ar_report_no,
                        ar_dd, ar_mm, ar_yy, ar_iso,
                        di_memo_no, m_dd, m_mm, m_yy, m_iso,
                        govt_analyst, extra_fees, monthly_id
                    ))

                    # If linked, mark monthly sample as DISPATCHED
                    if monthly_id:
                        conn.execute("""
                        UPDATE monthly_samples SET dispatch_status = 'DISPATCHED' WHERE id = ?;
                        """, (monthly_id,))

                    # Auto-seed manufacturer directory
                    if mfgname and licence:
                        alias = mfgname.split()[0].upper()
                        conn.execute("""
                        INSERT OR IGNORE INTO manufacturers (
                            short_name_alias, licence, mfgname, mfgadd1, mfgadd2, mfgadd3, distcd, statecd
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, (alias, licence, mfgname, mfgadd1, mfgadd2, mfgadd3, distcd, statecd))

                    total_ingested += 1

        wb.close()
        log_audit("INGEST_MASTER", path.name, details=f"Ingested {total_ingested} master records.")
        return total_ingested

    @classmethod
    def full_scan_workspace(cls, folder_path: Path | str) -> Dict[str, Any]:
        """
        Scans a folder and ingests all monthly and master files.
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return {"error": f"Directory not found: {folder}"}

        monthly_files_scanned = 0
        master_files_scanned = 0
        total_monthly_rows = 0
        total_master_rows = 0

        # Scan for monthly files: check all xlsx except temp files and backups
        for f in folder.glob("*.xlsx"):
            if f.name.startswith("~$") or f.name.startswith(".tmp_"):
                continue

            stem = f.stem.upper()
            if "MASTER" in stem:
                master_rows = cls.read_master_file(f)
                master_files_scanned += 1
                total_master_rows += master_rows
            else:
                # Check if it has monthly tab names or month in filename
                is_monthly = any(m in stem for m in config.MONTH_NAMES) or "TEMPLATE" in stem
                if is_monthly:
                    monthly_rows = cls.read_monthly_file(f)
                    monthly_files_scanned += 1
                    total_monthly_rows += monthly_rows

        return {
            "status": "success",
            "monthly_files_scanned": monthly_files_scanned,
            "master_files_scanned": master_files_scanned,
            "total_monthly_rows": total_monthly_rows,
            "total_master_rows": total_master_rows,
        }
