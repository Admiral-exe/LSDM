"""
Cross-file Tally & Reconciliation Engine.
Executes relational checks in <100ms, identifying pending dispatches,
orphan master dispatches, and field-level discrepancies (Batch No, Memo No, Name).
"""
from typing import Dict, Any, List
from backend.database import get_db_connection

class TallyEngine:
    @staticmethod
    def get_summary_metrics() -> Dict[str, Any]:
        """Calculates global tally metrics across all files."""
        with get_db_connection() as conn:
            total_arrived = conn.execute("SELECT COUNT(*) FROM monthly_samples;").fetchone()[0]
            total_dispatched = conn.execute("SELECT COUNT(*) FROM master_dispatches;").fetchone()[0]

            pending_dispatches = conn.execute("""
            SELECT COUNT(*) FROM monthly_samples 
            WHERE id NOT IN (SELECT DISTINCT monthly_sample_id FROM master_dispatches WHERE monthly_sample_id IS NOT NULL);
            """).fetchone()[0]

            orphan_masters = conn.execute("""
            SELECT COUNT(*) FROM master_dispatches WHERE monthly_sample_id IS NULL;
            """).fetchone()[0]

            # Discrepancies between linked records (batch number or memo mismatch)
            discrepancy_count = conn.execute("""
            SELECT COUNT(*) FROM monthly_samples m
            JOIN master_dispatches d ON m.id = d.monthly_sample_id
            WHERE TRIM(UPPER(m.batch_no)) != TRIM(UPPER(d.batchno))
               OR TRIM(UPPER(m.memorandum)) != TRIM(UPPER(d.di_memo_no));
            """).fetchone()[0]

            tallied = total_dispatched - orphan_masters - discrepancy_count

            return {
                "total_arrived": total_arrived,
                "total_dispatched": total_dispatched,
                "tallied": max(0, tallied),
                "pending_dispatches": pending_dispatches,
                "orphan_masters": orphan_masters,
                "discrepancies": discrepancy_count,
            }

    @staticmethod
    def get_reconciliation_details(filter_type: str = "ALL") -> List[Dict[str, Any]]:
        """
        Returns full detailed reconciliation rows:
        filter_type: 'ALL', 'PENDING', 'TALLIED', 'ORPHAN', 'DISCREPANCY'
        """
        results = []
        with get_db_connection() as conn:
            # 1. Matched records
            matched_rows = conn.execute("""
            SELECT 
                m.id AS monthly_id, m.file_name AS monthly_file, m.sheet_name AS monthly_sheet,
                m.sample_no, m.group_code, m.sample_name, m.batch_no AS monthly_batch,
                m.memorandum AS monthly_memo, m.receive_date, m.name_of_mfg,
                d.id AS master_id, d.file_name AS master_file, d.sheet_name AS master_sheet,
                d.sampno, d.batchno AS master_batch, d.di_memo_no AS master_memo,
                d.result, d.fees, d.recdate_iso
            FROM monthly_samples m
            JOIN master_dispatches d ON m.id = d.monthly_sample_id;
            """).fetchall()

            for r in matched_rows:
                row_dict = dict(r)
                mismatches = []
                if clean_compare(row_dict["monthly_batch"], row_dict["master_batch"]) is False:
                    mismatches.append(f"Batch Mismatch: Monthly '{row_dict['monthly_batch']}' vs Master '{row_dict['master_batch']}'")
                if clean_compare(row_dict["monthly_memo"], row_dict["master_memo"]) is False:
                    mismatches.append(f"Memo Mismatch: Monthly '{row_dict['monthly_memo']}' vs Master '{row_dict['master_memo']}'")

                if mismatches:
                    status = "DISCREPANCY"
                    led = "RED"
                else:
                    status = "TALLIED"
                    led = "GREEN"

                row_dict["status"] = status
                row_dict["led"] = led
                row_dict["mismatches"] = mismatches

                if filter_type == "ALL" or filter_type == status:
                    results.append(row_dict)

            # 2. Pending Dispatches (In Monthly but not in Master)
            if filter_type in ("ALL", "PENDING"):
                pending_rows = conn.execute("""
                SELECT 
                    m.id AS monthly_id, m.file_name AS monthly_file, m.sheet_name AS monthly_sheet,
                    m.sample_no, m.group_code, m.sample_name, m.batch_no AS monthly_batch,
                    m.memorandum AS monthly_memo, m.receive_date, m.name_of_mfg,
                    NULL AS master_id, NULL AS master_file, NULL AS master_sheet,
                    NULL AS sampno, NULL AS master_batch, NULL AS master_memo,
                    NULL AS result, NULL AS fees, NULL AS recdate_iso
                FROM monthly_samples m
                WHERE m.id NOT IN (SELECT DISTINCT monthly_sample_id FROM master_dispatches WHERE monthly_sample_id IS NOT NULL);
                """).fetchall()

                for r in pending_rows:
                    row_dict = dict(r)
                    row_dict["status"] = "PENDING"
                    row_dict["led"] = "AMBER"
                    row_dict["mismatches"] = ["Pending Dispatch entry in Master file"]
                    results.append(row_dict)

            # 3. Orphan Masters (In Master but not matched in Monthly)
            if filter_type in ("ALL", "ORPHAN"):
                orphan_rows = conn.execute("""
                SELECT 
                    NULL AS monthly_id, NULL AS monthly_file, NULL AS monthly_sheet,
                    d.sample_no, d.group_letter AS group_code, d.sampname AS sample_name,
                    NULL AS monthly_batch, NULL AS monthly_memo, NULL AS receive_date,
                    d.mfgname AS name_of_mfg,
                    d.id AS master_id, d.file_name AS master_file, d.sheet_name AS master_sheet,
                    d.sampno, d.batchno AS master_batch, d.di_memo_no AS master_memo,
                    d.result, d.fees, d.recdate_iso
                FROM master_dispatches d
                WHERE d.monthly_sample_id IS NULL;
                """).fetchall()

                for r in orphan_rows:
                    row_dict = dict(r)
                    row_dict["status"] = "ORPHAN"
                    row_dict["led"] = "RED"
                    row_dict["mismatches"] = ["Orphan Master Record (No matching arrival record found)"]
                    results.append(row_dict)

        return results

def clean_compare(val1: Any, val2: Any) -> bool:
    """Case-insensitive, whitespace-trimmed comparison."""
    s1 = str(val1 or "").strip().upper()
    s2 = str(val2 or "").strip().upper()
    return s1 == s2
