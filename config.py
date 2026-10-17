"""
Configuration and constants for Supply Chain & Laboratory Sample Management System.
"""
import sys
from pathlib import Path
import version

# Detect execution mode (Development vs PyInstaller Frozen Bundle)
if getattr(sys, "frozen", False):
    INSTALL_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", INSTALL_DIR))
    BASE_DIR = INSTALL_DIR
else:
    INSTALL_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = INSTALL_DIR
    BASE_DIR = INSTALL_DIR

DB_PATH = BASE_DIR / "supply_management.db"
BACKUP_DIR = BASE_DIR / ".backups"

def get_resource_path(relative_name: str) -> Path:
    """Finds resource file whether running in development or PyInstaller frozen bundle."""
    p_install = INSTALL_DIR / relative_name
    if p_install.exists():
        return p_install
    p_bundle = BUNDLE_DIR / relative_name
    if p_bundle.exists():
        return p_bundle
    return p_install

# Server configuration
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

# Gujarat District Code Lookup Table
GUJARAT_DISTRICTS = {
    1: "JAMNAGAR",
    2: "RAJKOT",
    4: "BHAVNAGAR",
    5: "AMRELI",
    6: "JUNAGADH",
    7: "BHUJ",
    9: "HIMATNAGAR",
    10: "PATAN",
    11: "AHMEDABAD RURAL",
    12: "AHMEDABAD",
    13: "NADIAD",
    14: "GODHARA",
    15: "VADODARA",
    16: "BHARUCH",
    17: "SURAT",
    18: "VALSAD",
}

DISTRICT_NAME_TO_CODE = {name: code for code, name in GUJARAT_DISTRICTS.items()}

# Sample Groups Mapping
SAMPLE_GROUPS = ["DI", "CMSO", "PDT", "UO", "ESIS"]

TAB_NAME_TO_GROUP_CODE = {
    "D.I.": "DI",
    "CMSO": "CMSO",
    "PDT": "PDT",
    "U.O.": "UO",
    "ESIS": "ESIS",
}

GROUP_CODE_TO_TAB_NAME = {v: k for k, v in TAB_NAME_TO_GROUP_CODE.items()}

# Mapping from group code to master prefix letter
GROUP_CODE_TO_MASTER_LETTER = {
    "DI": "D",
    "CMSO": "C",
    "PDT": "P",
    "UO": "UO",
    "ESIS": "E",
}

MASTER_LETTER_TO_GROUP_CODE = {
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

# Master sheet routing
GROUP_CODE_TO_MASTER_SHEET = {
    "DI": "DI CMSO UO",
    "CMSO": "DI CMSO UO",
    "UO": "DI CMSO UO",
    "ESIS": "DI CMSO UO",
    "PDT": "PDT",
}

# Strict String columns (OpenPyXL explicit '@' format)
STRICT_STRING_COLUMNS = {
    "BATCH NO",
    "BATHCH NO",
    "BATCHNO",
    "SAMPNO",
    "LICENCE",
    "MEMORANDUM",
    "DI MEMO NO",
}

# Month names for discovery and sorting
MONTH_NAMES = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
]
