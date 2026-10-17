"""
Database module: SQLite WAL mode connection, schema initialization, and row index re-sequencing.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import config

def get_db_path() -> Path:
    return config.DB_PATH

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with WAL mode and row factory."""
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables, default lookups, and performance indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Configuration & Workspace State
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Default configuration seeds
        cursor.execute("""
        INSERT OR IGNORE INTO app_config (key, value) VALUES 
        ('workspace_folder_path', ?),
        ('active_year', '2026'),
        ('master_file_name', 'MASTER_TEMPLATE.xlsx');
        """, (str(config.BASE_DIR),))

        # 2. Gujarat District Reference Directory
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            district_code INTEGER PRIMARY KEY,
            district_name TEXT NOT NULL UNIQUE
        );
        """)

        for code, name in config.GUJARAT_DISTRICTS.items():
            cursor.execute(
                "INSERT OR IGNORE INTO districts (district_code, district_name) VALUES (?, ?);",
                (code, name)
            )

        # 3. Smart Manufacturer Directory (7-Field Auto-Memory)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_name_alias TEXT NOT NULL UNIQUE,
            licence TEXT NOT NULL,
            mfgname TEXT NOT NULL,
            mfgadd1 TEXT,
            mfgadd2 TEXT,
            mfgadd3 TEXT,
            distcd TEXT,
            statecd TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Drug Inspectors Directory
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspector_name TEXT NOT NULL UNIQUE,
            default_district_name TEXT,
            default_district_code INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 5. Monthly Sample Arrival Register
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            month_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            sheet_name TEXT NOT NULL,
            group_code TEXT NOT NULL,
            excel_row_idx INTEGER NOT NULL,
            sr_no INTEGER NOT NULL,
            receive_date TEXT,
            sample_no INTEGER NOT NULL,
            division TEXT,
            tp_proce TEXT,
            catgo_name TEXT,
            catego_no TEXT,
            g_og TEXT,
            sample_name TEXT NOT NULL,
            batch_no TEXT NOT NULL,
            exp_date TEXT,
            name_of_mfg TEXT,
            di_name_city TEXT,
            inspector_name TEXT,
            city_district TEXT,
            memorandum TEXT NOT NULL,
            distributed_to TEXT,
            distribution_date TEXT,
            weightage TEXT,
            dispatch_status TEXT DEFAULT 'PENDING' CHECK (dispatch_status IN ('PENDING', 'DISPATCHED', 'MISMATCH')),
            sync_status TEXT DEFAULT 'SYNCED' CHECK (sync_status IN ('SYNCED', 'DIRTY', 'ERROR')),
            last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, group_code, sample_no)
        );
        """)

        # 6. Master Testing & Dispatch Register
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            excel_row_idx INTEGER NOT NULL,
            sampno TEXT NOT NULL UNIQUE,
            sampno_raw TEXT,
            year_prefix INTEGER NOT NULL,
            group_letter TEXT NOT NULL,
            sample_no INTEGER NOT NULL,
            recdate_dd INTEGER, recdate_mm INTEGER, recdate_yyyy INTEGER,
            recdate_iso TEXT,
            sampdate_dd INTEGER, sampdate_mm INTEGER, sampdate_yyyy INTEGER,
            sampdate_iso TEXT,
            type TEXT,
            namecd TEXT,
            sender_name TEXT,
            distocd INTEGER,
            distoname TEXT,
            placecd TEXT,
            placenm TEXT,
            sampname TEXT NOT NULL,
            batchno TEXT NOT NULL,
            licence TEXT,
            col18_blank TEXT,
            mfgname TEXT,
            mfgadd1 TEXT,
            mfgadd2 TEXT,
            mfgadd3 TEXT,
            distcd TEXT,
            statecd TEXT,
            testrepo_q TEXT DEFAULT 'Q',
            testrepo_quarter INTEGER,
            testrepo_no TEXT,
            testrepo_yyyy INTEGER,
            testrepo_group TEXT,
            testdate_dd INTEGER, testdate_mm INTEGER, testdate_yyyy INTEGER,
            testdate_iso TEXT,
            result INTEGER,
            nsq TEXT,
            det1_nsq TEXT,
            fees TEXT,
            ar_report_no TEXT,
            ar_report_date_dd INTEGER, ar_report_date_mm INTEGER, ar_report_date_yyyy INTEGER,
            ar_report_date_iso TEXT,
            di_memo_no TEXT,
            di_memo_date_dd INTEGER, di_memo_date_mm INTEGER, di_memo_date_yyyy INTEGER,
            di_memo_date_iso TEXT,
            govt_analyst TEXT,
            extra_fees TEXT,
            monthly_sample_id INTEGER REFERENCES monthly_samples(id) ON DELETE SET NULL,
            sync_status TEXT DEFAULT 'SYNCED' CHECK (sync_status IN ('SYNCED', 'DIRTY', 'ERROR')),
            last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 7. Audit Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            target_file TEXT NOT NULL,
            backup_path TEXT,
            details TEXT
        );
        """)

        # Performance Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_link ON monthly_samples(year, group_code, sample_no);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_batch ON monthly_samples(batch_no);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_memo ON monthly_samples(memorandum);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_monthly_file_row ON monthly_samples(file_name, sheet_name, excel_row_idx);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_master_link ON master_dispatches(year_prefix, group_letter, sample_no);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_master_sampno ON master_dispatches(sampno);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_master_batch ON master_dispatches(batchno);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_master_file_row ON master_dispatches(file_name, sheet_name, excel_row_idx);")

def get_config_val(key: str, default: str = "") -> str:
    """Retrieve a config value from SQLite."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT value FROM app_config WHERE key = ?;", (key,)).fetchone()
        return row["value"] if row else default

def set_config_val(key: str, value: str):
    """Set or update a config value in SQLite."""
    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO app_config (key, value, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP;
        """, (key, value))

def resequence_monthly_rows(file_name: str, sheet_name: str, deleted_excel_row_idx: int):
    """
    Shifts row indices up by 1 and decrements serial number for rows below a deleted row.
    """
    with get_db_connection() as conn:
        conn.execute("""
        UPDATE monthly_samples
        SET excel_row_idx = excel_row_idx - 1,
            sr_no = sr_no - 1
        WHERE file_name = ? AND sheet_name = ? AND excel_row_idx > ?;
        """, (file_name, sheet_name, deleted_excel_row_idx))

def resequence_master_rows(file_name: str, sheet_name: str, deleted_excel_row_idx: int):
    """
    Shifts master row indices up by 1 for rows below a deleted row.
    """
    with get_db_connection() as conn:
        conn.execute("""
        UPDATE master_dispatches
        SET excel_row_idx = excel_row_idx - 1
        WHERE file_name = ? AND sheet_name = ? AND excel_row_idx > ?;
        """, (file_name, sheet_name, deleted_excel_row_idx))

def log_audit(action: str, target_file: str, backup_path: str = "", details: str = ""):
    """Logs atomic file operations for auditability."""
    with get_db_connection() as conn:
        conn.execute("""
        INSERT INTO sync_audit_log (action, target_file, backup_path, details)
        VALUES (?, ?, ?, ?);
        """, (action, target_file, backup_path, details))
