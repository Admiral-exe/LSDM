"""
Smart Auto-Memory Service.
Manages 7-field Manufacturer profiles and Drug Inspector & Gujarat District lookups.
"""
from typing import Dict, Any, List, Optional
import config
from backend.database import get_db_connection

class MemoryService:
    @staticmethod
    def get_all_districts() -> List[Dict[str, Any]]:
        """Returns the standard Gujarat district reference table."""
        return [
            {"code": code, "name": name}
            for code, name in sorted(config.GUJARAT_DISTRICTS.items(), key=lambda x: x[0])
        ]

    @staticmethod
    def resolve_district(input_val: str | int) -> tuple[Optional[int], str]:
        """Resolves district input (name or code) to (district_code, district_name)."""
        if not input_val:
            return None, ""
        # Check if code
        try:
            code = int(input_val)
            if code in config.GUJARAT_DISTRICTS:
                return code, config.GUJARAT_DISTRICTS[code]
        except (ValueError, TypeError):
            pass

        # Check by name
        clean_name = str(input_val).strip().upper()
        if clean_name in config.DISTRICT_NAME_TO_CODE:
            return config.DISTRICT_NAME_TO_CODE[clean_name], clean_name

        # Partial match
        for name, code in config.DISTRICT_NAME_TO_CODE.items():
            if clean_name in name or name in clean_name:
                return code, name

        return None, clean_name

    @staticmethod
    def get_manufacturer(short_alias: str) -> Optional[Dict[str, Any]]:
        """Looks up a manufacturer by short name alias."""
        if not short_alias:
            return None
        alias_clean = short_alias.strip().upper()
        with get_db_connection() as conn:
            row = conn.execute("""
            SELECT * FROM manufacturers WHERE UPPER(short_name_alias) = ?;
            """, (alias_clean,)).fetchone()
            if row:
                return dict(row)
            # Try matching substring
            row = conn.execute("""
            SELECT * FROM manufacturers 
            WHERE UPPER(short_name_alias) LIKE ? OR UPPER(mfgname) LIKE ?
            LIMIT 1;
            """, (f"%{alias_clean}%", f"%{alias_clean}%")).fetchone()
            return dict(row) if row else None

    @staticmethod
    def search_manufacturers(query: str) -> List[Dict[str, Any]]:
        """Returns auto-complete matches for manufacturer aliases or names."""
        clean_q = query.strip().upper()
        with get_db_connection() as conn:
            rows = conn.execute("""
            SELECT * FROM manufacturers 
            WHERE UPPER(short_name_alias) LIKE ? OR UPPER(mfgname) LIKE ?
            ORDER BY short_name_alias ASC LIMIT 20;
            """, (f"%{clean_q}%", f"%{clean_q}%")).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def save_manufacturer(data: Dict[str, Any]) -> Dict[str, Any]:
        """Inserts or updates a manufacturer profile in memory."""
        alias = str(data.get("short_name_alias", "")).strip().upper()
        licence = str(data.get("licence", "")).strip()
        mfgname = str(data.get("mfgname", "")).strip().upper()
        mfgadd1 = str(data.get("mfgadd1", "")).strip()
        mfgadd2 = str(data.get("mfgadd2", "")).strip()
        mfgadd3 = str(data.get("mfgadd3", "")).strip()
        distcd = str(data.get("distcd", "")).strip()
        statecd = str(data.get("statecd", "")).strip()

        if not alias:
            alias = mfgname.split()[0] if mfgname else "UNKNOWN"

        with get_db_connection() as conn:
            conn.execute("""
            INSERT INTO manufacturers (
                short_name_alias, licence, mfgname, mfgadd1, mfgadd2, mfgadd3, distcd, statecd, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(short_name_alias) DO UPDATE SET
                licence = excluded.licence,
                mfgname = excluded.mfgname,
                mfgadd1 = excluded.mfgadd1,
                mfgadd2 = excluded.mfgadd2,
                mfgadd3 = excluded.mfgadd3,
                distcd = excluded.distcd,
                statecd = excluded.statecd,
                updated_at = CURRENT_TIMESTAMP;
            """, (alias, licence, mfgname, mfgadd1, mfgadd2, mfgadd3, distcd, statecd))

            row = conn.execute("SELECT * FROM manufacturers WHERE short_name_alias = ?;", (alias,)).fetchone()
            return dict(row)

    @staticmethod
    def search_inspectors(query: str) -> List[Dict[str, Any]]:
        """Returns auto-complete suggestions for Drug Inspector names."""
        clean_q = query.strip().upper()
        with get_db_connection() as conn:
            rows = conn.execute("""
            SELECT * FROM inspectors 
            WHERE UPPER(inspector_name) LIKE ?
            ORDER BY inspector_name ASC LIMIT 20;
            """, (f"%{clean_q}%",)).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def save_inspector(name: str, district_name: str = "", district_code: Optional[int] = None) -> Dict[str, Any]:
        """Saves or updates an inspector with default district."""
        clean_name = name.strip()
        with get_db_connection() as conn:
            conn.execute("""
            INSERT INTO inspectors (inspector_name, default_district_name, default_district_code)
            VALUES (?, ?, ?)
            ON CONFLICT(inspector_name) DO UPDATE SET
                default_district_name = excluded.default_district_name,
                default_district_code = excluded.default_district_code;
            """, (clean_name, district_name, district_code))
            row = conn.execute("SELECT * FROM inspectors WHERE inspector_name = ?;", (clean_name,)).fetchone()
            return dict(row)
