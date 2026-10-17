# Enterprise Supply Chain & Laboratory Sample Management Desktop System
## Comprehensive Technical Implementation Plan (Revision 2.0)

---

### Executive Summary & Template Inspection Findings

A thorough byte-level and cell-level inspection of `APRIL_TEMPLATE.xlsx` and `MASTER_TEMPLATE.xlsx` was conducted using `openpyxl`. The findings confirm several critical architectural, schema, and domain nuances that the ingestion, synchronization, and UI engines must handle with 100% precision:

1. **Monthly Arrival File (`APRIL_TEMPLATE.xlsx`):**
   * **5 Tabs:** `D.I.`, `CMSO`, `PDT`, `U.O.`, `ESIS`.
   * **The ESIS Tab Shift (Missing Group Column):** In `D.I.`, `CMSO`, `PDT`, and `U.O.`, Column 1 (`A`) is an unlabelled group tag containing the group acronym (`'DI'`, `'CMSO'`, `'PDT'`, `'UO'`), and Serial No begins at Column 2 (`B`). In `ESIS`, Column 1 (`A`) is `SR.    NO` directly. Every logical field in `ESIS` is shifted one column to the left (17 columns total vs 18 columns in other tabs).
   * **Header Typos and Whitespace Variations:**
     * Serial No: `'SR. NO'` in `D.I.`, but `'SR.    NO'` (4 spaces) in `CMSO`, `PDT`, `U.O.`, and `ESIS`.
     * Batch No: misspelled `'BATHCH NO'` in `D.I.`, `CMSO`, `U.O.`, and `ESIS`, but `'BATCH NO'` in `PDT`.
     * Spaced headers: `'SAMPLE       NO'` (7 spaces), `'EXP         DATE'` (9 spaces), `'RECEIVE  DATE'` (2 spaces).
   * **Row Offset:** Data rows start strictly at **Row 2** (Row 1 contains headers).
   * **Numbering Integrity:** `SR. NO` and `SAMPLE NO` must be stored and treated as sequential integers (e.g. 1481, 1482...) to support multi-month chronological auto-increment (`MAX(sample_no) + 1`), while `BATCH NO`, `MEMORANDUM`, and `LICENCE` are strictly forced to explicit text (`@`).

2. **Master Dispatch File (`MASTER_TEMPLATE.xlsx`):**
   * **2 Active Tabs:** `DI CMSO UO` and `PDT` (plus an unused blank `Sheet1`).
   * **Routing Rule:** Samples from `D.I.`, `CMSO`, `U.O.`, and `ESIS` route to `DI CMSO UO`. Samples from `PDT` route to `PDT`.
   * **2-Row Header Structure:** Primary section headers reside on Row 1; sub-headers (`DD`, `MM`, `YYYY`, `Q`, `1,2,3,4`, `NO.`, `GOVERNMENT ANALYST`, etc.) reside on Row 2. Data rows **must start strictly at Row 3**.
   * **Multi-Column Split Dates:** 5 date fields are split across 3 adjacent integer columns (`DD`, `MM`, `YYYY`):
     * `RECDATE`: Columns 2, 3, 4 (`B`, `C`, `D`)
     * `SAMPDATE`: Columns 5, 6, 7 (`E`, `F`, `G`)
     * `TESTDATE`: Columns 30, 31, 32 (`AD`, `AE`, `AF`)
     * `AR REPORT DATE`: Columns 38, 39, 40 (`AL`, `AM`, `AN`)
     * `DI MEMO DATE`: Columns 42, 43, 44 (`AP`, `AQ`, `AR`)
   * **Multi-Column `TESTREPO` Matrix:** Test report details span 5 columns (Columns 25–29: `Y`, `Z`, `AA`, `AB`, `AC`):
     * Col 25 (`Y`): Fixed identifier `'Q'`
     * Col 26 (`Z`): Quarter integer (`1, 2, 3, 4`)
     * Col 27 (`AA`): Report Number (`NO.`)
     * Col 28 (`AB`): 4-digit Year (`YYYY`)
     * Col 29 (`AC`): Group Code (`'DI'`, `'CMSO'`, `'UO'`, `'ESIS'`, `'PDT'`)
   * **Spacer Column 18 (`R`):** Column 18 is completely unlabelled and empty in both sheets. Must remain untouched as an empty column to preserve cell alignment.
   * **Critical Domain Format Rules:**
     * **Column 33 (`RESULT`):** Stores numeric code: `1` = Standard Quality, `2` = Not of Standard Quality (NSQ). The GUI displays human-readable options `1 - Standard Quality` and `2 - NSQ`, but writes integer `1` or `2` to Excel.
     * **Column 36 (`FEES`):** Can be a numeric value (e.g. `1390`, `3850`) OR the string `"NIL"`. Stored as `TEXT` in SQLite and Excel to guarantee zero type-conversion failures.
     * **Legacy Typo Normalization in `SAMPNO` (`26DO729` -> `26D0729`):** Operators frequently typed `'O'` instead of `'0'` after the group code. If the group code matches `DO`, `CO`, `PO`, or `EO`, the parser strips the trailing `'O'` into a leading `'0'` for the sample number (`Year=26`, `Group=D`, `Sample=729`), while correctly preserving `UO` as U.O.
     * **Sheet Differences between `DI CMSO UO` (45 cols) and `PDT` (46 cols):**
       * Column 10 (`J`): Header is `'NAME'` on `DI CMSO UO`; `'SENDER NAME'` on `PDT`.
       * Column 31 (`AE`): Sub-header is `'MM'` on `DI CMSO UO`; blank on `PDT`.
       * Column 46 (`AT`): Extra `'FEES'` column present **only on PDT**.

3. **100% Offline Operational Guarantee:**
   * Software runs in secure, air-gapped office environments without internet access.
   * Zero external CDN links: No Tailwind CDN, no Google Fonts, no unpkg/cdnjs, no external icon requests.
   * Strictly local Vanilla CSS files, inline SVGs for iconography, and standard native offline Windows typography (`Segoe UI`, `Cascadia Code`, `Consolas`).

---

## 1. Modular File Structure & Architectural Hierarchy

To ensure maximum maintainability, separation of concerns, and clean developer inspection, the codebase is strictly organized into decoupled, single-responsibility modules:

```text
SupplyManagement/
├── main.py                      # Application entry point (FastAPI server + PyWebView desktop window)
├── config.py                    # Constants, default paths, column mappings, Gujarat district dictionary
├── IMPLEMENTATION_PLAN.md       # Approved technical implementation plan
├── .backups/                    # Automated rolling timestamped Excel snapshots (max 50)
├── backend/
│   ├── __init__.py
│   ├── database.py              # SQLite WAL connection, table initialization, and row index re-sequencing
│   ├── models.py                # Pydantic schemas for data validation and API contracts
│   ├── excel_lock.py            # ~$ lockfile & msvcrt OS file handle lock detector
│   ├── excel_backup.py          # Timestamped rolling backup manager (.backups/)
│   ├── excel_reader.py          # Ingestion engine (reads Monthly & Master .xlsx into SQLite)
│   ├── excel_writer.py          # Atomic 2-way .xlsx writer (.tmp -> verify -> os.replace)
│   ├── tally_engine.py          # Sub-100ms cross-file reconciliation & discrepancy detection
│   ├── memory_service.py        # Smart Manufacturer (7-field) & Inspector/District auto-memory
│   └── routes/
│       ├── arrival_routes.py    # CRUD for Workspace 1 (Monthly Arrivals + New Month File creator)
│       ├── dispatch_routes.py   # CRUD for Workspace 2 (Master Testing & Dispatch)
│       ├── tally_routes.py      # Endpoints for Workspace 3 (Reconciliation & Auto-Repair)
│       └── directory_routes.py  # Endpoints for Workspace 4 (Manufacturers, Inspectors, Audit Logs)
└── frontend/
    ├── index.html               # Main shell layout (100% offline, zero external CDN calls)
    ├── css/
    │   ├── variables.css        # Neo-skeuomorphic design tokens, bevels, LEDs, offline fonts
    │   ├── components.css       # Tactile 3D buttons, recessed wells, physical folder index tabs
    │   └── workspaces.css       # Grid layouts for Workspaces 1, 2, 3, and 4
    └── js/
        ├── app.js               # Global state, workspace router, WebSocket/API client, hotkeys
        ├── arrival_workspace.js # Workspace 1 logic (Monthly register, rapid keyboard navigation)
        ├── dispatch_workspace.js# Workspace 2 logic (One-click dispatch, locked plate, test form)
        ├── tally_workspace.js   # Workspace 3 logic (Reconciliation dashboard & side-by-side diff)
        └── directory_workspace.js# Workspace 4 logic (Manufacturer & Inspector management)
```

---

## 2. Complete SQLite Database Schema (WAL Mode)

```sql
-- ============================================================================
-- 1. CONFIGURATION & WORKSPACE PATH STATE
-- ============================================================================
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default configuration seeds
INSERT OR IGNORE INTO app_config (key, value) VALUES 
('workspace_folder_path', '.'),
('active_year', '2026'),
('master_file_name', 'MASTER_TEMPLATE.xlsx');

-- ============================================================================
-- 2. GUJARAT DISTRICT DIRECTORY (Standard Reference Lookup)
-- ============================================================================
CREATE TABLE IF NOT EXISTS districts (
    district_code INTEGER PRIMARY KEY,
    district_name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO districts (district_code, district_name) VALUES
(1, 'JAMNAGAR'), (2, 'RAJKOT'), (4, 'BHAVNAGAR'), (5, 'AMRELI'),
(6, 'JUNAGADH'), (7, 'BHUJ'), (9, 'HIMATNAGAR'), (10, 'PATAN'),
(11, 'AHMEDABAD RURAL'), (12, 'AHMEDABAD'), (13, 'NADIAD'),
(14, 'GODHARA'), (15, 'VADODARA'), (16, 'BHARUCH'), (17, 'SURAT'), (18, 'VALSAD');

-- ============================================================================
-- 3. SMART MANUFACTURER DIRECTORY (7-Field Auto-Memory)
-- ============================================================================
CREATE TABLE IF NOT EXISTS manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_name_alias TEXT NOT NULL UNIQUE, -- Normalized uppercase (e.g., 'NESTOR PHARMA')
    licence TEXT NOT NULL,                 -- Stored strictly as explicit text
    mfgname TEXT NOT NULL,                 -- Formal corporate name (e.g., 'NESTOR PHARMACEUTICALS LTD.')
    mfgadd1 TEXT,
    mfgadd2 TEXT,
    mfgadd3 TEXT,
    distcd TEXT,
    statecd TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 4. DRUG INSPECTORS DIRECTORY
-- ============================================================================
CREATE TABLE IF NOT EXISTS inspectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspector_name TEXT NOT NULL UNIQUE,
    default_district_name TEXT,
    default_district_code INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. MONTHLY SAMPLE ARRIVAL REGISTER
-- ============================================================================
CREATE TABLE IF NOT EXISTS monthly_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,               -- e.g., 'APRIL 2026.xlsx'
    month_name TEXT NOT NULL,              -- e.g., 'APRIL'
    year INTEGER NOT NULL,                 -- e.g., 2026
    sheet_name TEXT NOT NULL,              -- 'D.I.', 'CMSO', 'PDT', 'U.O.', 'ESIS'
    group_code TEXT NOT NULL,              -- 'DI', 'CMSO', 'PDT', 'UO', 'ESIS'
    excel_row_idx INTEGER NOT NULL,        -- Physical row index in Excel (>= 2)
    sr_no INTEGER NOT NULL,                -- Tab serial number (sequential integer)
    receive_date TEXT,                     -- ISO 'YYYY-MM-DD'
    sample_no INTEGER NOT NULL,            -- Chronological sequential integer (unique per group & year)
    division TEXT,
    tp_proce TEXT,
    catgo_name TEXT,
    catego_no TEXT,
    g_og TEXT,
    sample_name TEXT NOT NULL,             -- 'SAMPLE NAME /GENERIC NAME'
    batch_no TEXT NOT NULL,                -- Stored strictly as text (e.g., '5E02')
    exp_date TEXT,                         -- Explicit text
    name_of_mfg TEXT,                      -- Short manufacturer name as typed
    di_name_city TEXT,                     -- Raw: "ABC (JAMNAGAR)"
    inspector_name TEXT,                   -- Extracted: "ABC"
    city_district TEXT,                    -- Extracted: "JAMNAGAR"
    memorandum TEXT NOT NULL,              -- Stored strictly as text
    distributed_to TEXT,
    distribution_date TEXT,
    weightage TEXT,
    dispatch_status TEXT DEFAULT 'PENDING' CHECK (dispatch_status IN ('PENDING', 'DISPATCHED', 'MISMATCH')),
    sync_status TEXT DEFAULT 'SYNCED' CHECK (sync_status IN ('SYNCED', 'DIRTY', 'ERROR')),
    last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year, group_code, sample_no)
);

-- ============================================================================
-- 6. MASTER TESTING & DISPATCH REGISTER
-- ============================================================================
CREATE TABLE IF NOT EXISTS master_dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,               -- e.g., 'Master 2026.xlsx'
    sheet_name TEXT NOT NULL,              -- 'DI CMSO UO' or 'PDT'
    excel_row_idx INTEGER NOT NULL,        -- Physical row index in Excel (>= 3)
    sampno TEXT NOT NULL UNIQUE,           -- Standard YYTS (e.g., '26C1484')
    sampno_raw TEXT,                       -- Preserves historical raw value e.g. '26DO729[10/IBC]'
    year_prefix INTEGER NOT NULL,          -- e.g., 26 -> 2026
    group_letter TEXT NOT NULL,            -- 'D', 'C', 'U', 'UO', 'E', 'P'
    sample_no INTEGER NOT NULL,            -- S integer linking to monthly_samples
    
    -- Split Date: RECDATE (Cols 2, 3, 4)
    recdate_dd INTEGER, recdate_mm INTEGER, recdate_yyyy INTEGER,
    recdate_iso TEXT,
    
    -- Split Date: SAMPDATE (Cols 5, 6, 7)
    sampdate_dd INTEGER, sampdate_mm INTEGER, sampdate_yyyy INTEGER,
    sampdate_iso TEXT,
    
    type TEXT,                             -- Col 8
    namecd TEXT,                           -- Col 9
    sender_name TEXT,                      -- Col 10 ('NAME' on DI CMSO UO, 'SENDER NAME' on PDT)
    distocd INTEGER,                       -- Col 11 (Gujarat District Code)
    distoname TEXT,                        -- Col 12 (District Name)
    placecd TEXT,                          -- Col 13
    placenm TEXT,                          -- Col 14
    sampname TEXT NOT NULL,                -- Col 15 (Transferred from Monthly Arrival)
    batchno TEXT NOT NULL,                 -- Col 16 (Transferred from Monthly Arrival, strictly Text)
    licence TEXT,                          -- Col 17 (From Manufacturer Memory, strictly Text)
    col18_blank TEXT,                      -- Col 18 (Unused spacer column)
    mfgname TEXT,                          -- Col 19 (Formal name from Manufacturer Memory)
    mfgadd1 TEXT,                          -- Col 20
    mfgadd2 TEXT,                          -- Col 21
    mfgadd3 TEXT,                          -- Col 22
    distcd TEXT,                           -- Col 23
    statecd TEXT,                          -- Col 24
    
    -- Multi-Column: TESTREPO (Cols 25 - 29)
    testrepo_q TEXT DEFAULT 'Q',           -- Col 25: Fixed 'Q'
    testrepo_quarter INTEGER,              -- Col 26: 1, 2, 3, 4
    testrepo_no TEXT,                      -- Col 27: Report No.
    testrepo_yyyy INTEGER,                 -- Col 28: 4-digit Year
    testrepo_group TEXT,                   -- Col 29: 'DI', 'CMSO', 'UO', 'ESIS', 'PDT'
    
    -- Split Date: TESTDATE (Cols 30, 31, 32)
    testdate_dd INTEGER, testdate_mm INTEGER, testdate_yyyy INTEGER,
    testdate_iso TEXT,
    
    result INTEGER,                        -- Col 33: 1 = Standard Quality, 2 = NSQ
    nsq TEXT,                              -- Col 34 (NSQ Flag / Category)
    det1_nsq TEXT,                         -- Col 35 (NSQ Defect Details)
    fees TEXT,                             -- Col 36: Stored as TEXT (supports "NIL" and numeric amounts e.g. "1390")
    ar_report_no TEXT,                     -- Col 37
    
    -- Split Date: AR REPORT DATE (Cols 38, 39, 40)
    ar_report_date_dd INTEGER, ar_report_date_mm INTEGER, ar_report_date_yyyy INTEGER,
    ar_report_date_iso TEXT,
    
    di_memo_no TEXT,                       -- Col 41 (Transferred from Monthly MEMORANDUM, strictly Text)
    
    -- Split Date: DI MEMO DATE (Cols 42, 43, 44)
    di_memo_date_dd INTEGER, di_memo_date_mm INTEGER, di_memo_date_yyyy INTEGER,
    di_memo_date_iso TEXT,
    
    govt_analyst TEXT,                     -- Col 45 (Government Analyst Name)
    extra_fees TEXT,                       -- Col 46 (PDT Sheet only: Stored as TEXT for "NIL" or numeric)
    
    monthly_sample_id INTEGER REFERENCES monthly_samples(id) ON DELETE SET NULL,
    sync_status TEXT DEFAULT 'SYNCED' CHECK (sync_status IN ('SYNCED', 'DIRTY', 'ERROR')),
    last_synced_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 7. PERFORMANCE INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_monthly_link ON monthly_samples(year, group_code, sample_no);
CREATE INDEX IF NOT EXISTS idx_monthly_batch ON monthly_samples(batch_no);
CREATE INDEX IF NOT EXISTS idx_monthly_memo ON monthly_samples(memorandum);
CREATE INDEX IF NOT EXISTS idx_monthly_file_row ON monthly_samples(file_name, sheet_name, excel_row_idx);
CREATE INDEX IF NOT EXISTS idx_master_link ON master_dispatches(year_prefix, group_letter, sample_no);
CREATE INDEX IF NOT EXISTS idx_master_sampno ON master_dispatches(sampno);
CREATE INDEX IF NOT EXISTS idx_master_batch ON master_dispatches(batchno);
CREATE INDEX IF NOT EXISTS idx_master_file_row ON master_dispatches(file_name, sheet_name, excel_row_idx);
```

---

## 3. Exact Column-Index Mapping Tables

### 3.1 Monthly Arrival File (`APRIL_TEMPLATE.xlsx`)
* Header row: **Row 1**. Data rows: **Row 2 onwards**.
* `SR. NO` and `SAMPLE NO`: Stored as pure sequential integers.
* `BATCH NO` and `MEMORANDUM`: Stored as explicit strings (`@`).

| Logical Field | Data Type | Standard Sheets (`D.I.`, `CMSO`, `PDT`, `U.O.`)<br/>1-Based Index & Letter | `ESIS` Sheet<br/>1-Based Index & Letter | Raw Template Header String |
| :--- | :--- | :---: | :---: | :--- |
| **Group Code Tag** | Text | **Col 1 (A)** | *N/A (Missing)* | `None` / `Unnamed: 0` |
| **Serial No** | **Integer** | **Col 2 (B)** | **Col 1 (A)** | `'SR. NO'` (D.I.) / `'SR.    NO'` (Others) |
| **Receive Date** | Date / Text | **Col 3 (C)** | **Col 2 (B)** | `'RECEIVE  DATE'` |
| **Sample No** | **Integer** | **Col 4 (D)** | **Col 3 (C)** | `'SAMPLE       NO'` |
| **Division** | Text | **Col 5 (E)** | **Col 4 (D)** | `'DIVISION'` |
| **T.P./Proce** | Text | **Col 6 (F)** | **Col 5 (E)** | `'T.P./PROCE'` |
| **Category Name** | Text | **Col 7 (G)** | **Col 6 (F)** | `'CATGO NAME'` |
| **Category No** | Text | **Col 8 (H)** | **Col 7 (G)** | `'CATEGO NO.'` |
| **G/OG** | Text | **Col 9 (I)** | **Col 8 (H)** | `'G/OG'` |
| **Sample Name** | Text | **Col 10 (J)** | **Col 9 (I)** | `'SAMPLE NAME /GENERIC NAME'` |
| **Batch No** | **Explicit Text (`@`)** | **Col 11 (K)** | **Col 10 (J)** | `'BATHCH NO'` (D.I., CMSO, U.O., ESIS) / `'BATCH NO'` (PDT) |
| **Expiry Date** | Text | **Col 12 (L)** | **Col 11 (K)** | `'EXP         DATE'` |
| **Manufacturer** | Text | **Col 13 (M)** | **Col 12 (L)** | `'NAME OF MFG'` |
| **DI Name (City)** | Text (`"ABC (XYZ)"`) | **Col 14 (N)** | **Col 13 (M)** | `'DI NAME (CITY)'` |
| **Memorandum** | **Explicit Text (`@`)** | **Col 15 (O)** | **Col 14 (N)** | `'MEMORANDUM'` |
| **Distributed To** | Text | **Col 16 (P)** | **Col 15 (O)** | `'DISTRIBUTED TO'` |
| **Distribution Date** | Date / Text | **Col 17 (Q)** | **Col 16 (P)** | `'DISTRIBUTION DATE'` |
| **Weightage** | Text | **Col 18 (R)** | **Col 17 (Q)** | `'WEIGHTAGE'` |

---

### 3.2 Master Testing & Dispatch File (`MASTER_TEMPLATE.xlsx`)
* Header rows: **Row 1** and **Row 2**. Data rows: **Row 3 onwards**.

| 1-Based Col | Col Letter | Row 1 Header | Row 2 Sub-Header | SQLite DB Column | Type / Format | Routing & Domain Rules |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **A** | `SAMPNO` | *Merged with R1* | `sampno` | **Explicit Text (`@`)** | Standard `YYTS` (e.g. `26C1484`). Typo normalizer handles `26DO729 -> 26D0729`. |
| **2** | **B** | `RECDATE` | `DD` | `recdate_dd` | Integer (1–31) | Split Date: Day |
| **3** | **C** | *Merged with B1* | `MM` | `recdate_mm` | Integer (1–12) | Split Date: Month |
| **4** | **D** | *Merged with B1* | `YYYY` | `recdate_yyyy` | Integer (4-digit) | Split Date: Year |
| **5** | **E** | `SAMPDATE` | `DD` | `sampdate_dd` | Integer (1–31) | Split Date: Day |
| **6** | **F** | *Merged with E1* | `MM` | `sampdate_mm` | Integer (1–12) | Split Date: Month |
| **7** | **G** | *Merged with E1* | `YYYY` | `sampdate_yyyy` | Integer (4-digit) | Split Date: Year |
| **8** | **H** | `TYPE` | *Merged with R1* | `type` | Text | Sample Type |
| **9** | **I** | `NAMECD` | *Merged with R1* | `namecd` | Text | Sender / Inspector Code |
| **10** | **J** | `NAME` / `SENDER NAME` | *Merged with R1* | `sender_name` | Text | Header is `'NAME'` on `DI CMSO UO`; `'SENDER NAME'` on `PDT`. |
| **11** | **K** | `DISTOCD` | *Merged with R1* | `distocd` | Integer | Gujarat District Code lookup (e.g. `1` for Jamnagar) |
| **12** | **L** | `DISTONAME` | *Merged with R1* | `distoname` | Text | District Name (e.g. `JAMNAGAR`) |
| **13** | **M** | `PLACECD` | *Merged with R1* | `placecd` | Text | Place Code |
| **14** | **N** | `PLACENM` | *Merged with R1* | `placenm` | Text | Place Name |
| **15** | **O** | `SAMPNAME` | *Merged with R1* | `sampname` | Text | Generic Drug Name (transferred from Monthly) |
| **16** | **P** | `BATCHNO` | *Merged with R1* | `batchno` | **Explicit Text (`@`)** | Batch Number (transferred from Monthly) |
| **17** | **Q** | `LICENCE` | *Merged with R1* | `licence` | **Explicit Text (`@`)** | Manufacturer Licence (from Smart Memory Directory) |
| **18** | **R** | *None* | *None* | `col18_blank` | Empty / Null | **Unused blank column**. Kept empty to preserve cell offset. |
| **19** | **S** | `MFGNAME` | *Merged with R1* | `mfgname` | Text | Formal Manufacturer Name |
| **20** | **T** | `MFGADD1` | *Merged with R1* | `mfgadd1` | Text | Manufacturer Address Line 1 |
| **21** | **U** | `MFGADD2` | *Merged with R1* | `mfgadd2` | Text | Manufacturer Address Line 2 |
| **22** | **V** | `MFGADD3` | *Merged with R1* | `mfgadd3` | Text | Manufacturer Address Line 3 |
| **23** | **W** | `DISTCD` | *Merged with R1* | `distcd` | Text | Manufacturer District Code |
| **24** | **X** | `STATECD` | *Merged with R1* | `statecd` | Text | Manufacturer State Code |
| **25** | **Y** | `TESTREPO` | `Q` | `testrepo_q` | Text | Constant `'Q'` |
| **26** | **Z** | *Merged with Y1* | `1,2,3,4` | `testrepo_quarter`| Integer | Test Quarter: 1, 2, 3, or 4 |
| **27** | **AA**| *Merged with Y1* | `NO.` | `testrepo_no` | Text | Report Number |
| **28** | **AB**| *Merged with Y1* | `YYYY` | `testrepo_yyyy` | Integer | 4-digit Year |
| **29** | **AC**| *Merged with Y1* | *None* | `testrepo_group` | Text | Group Code (`'DI'`, `'CMSO'`, `'UO'`, `'ESIS'`, `'PDT'`) |
| **30** | **AD**| `TESTDATE` | `DD` | `testdate_dd` | Integer (1–31) | Split Date: Day |
| **31** | **AE**| *Merged with AD1*| `MM` / *None* | `testdate_mm` | Integer (1–12) | Split Date: Month (Row 2 is `'MM'` in DI, None in PDT) |
| **32** | **AF**| *Merged with AD1*| `YYYY` | `testdate_yyyy` | Integer (4-digit) | Split Date: Year |
| **33** | **AG**| `RESULT` | *Merged with R1* | `result` | **Integer Code** | **`1` = Standard Quality, `2` = NSQ**. (Written as 1 or 2). |
| **34** | **AH**| `NSQ` | *Merged with R1* | `nsq` | Text | NSQ Classification Flag |
| **35** | **AI**| `DET1_NSQ` | *Merged with R1* | `det1_nsq` | Text | NSQ Defect Specifics |
| **36** | **AJ**| `FEES` | *Merged with R1* | `fees` | **Explicit Text** | **Stored as TEXT** (Supports numeric e.g. "1390" or string "NIL"). |
| **37** | **AK**| `AR REPORT NO` | *Merged with R1* | `ar_report_no` | Text | AR Report Identifier |
| **38** | **AL**| `AR REPORT DATE` | `DD` | `ar_report_date_dd` | Integer (1–31) | Split Date: Day |
| **39** | **AM**| *Merged with AL1*| `MM` | `ar_report_date_mm` | Integer (1–12) | Split Date: Month |
| **40** | **AN**| *Merged with AL1*| `YYYY` | `ar_report_date_yyyy`| Integer (4-digit) | Split Date: Year |
| **41** | **AO**| `DI MEMO NO` | *Merged with R1* | `di_memo_no` | **Explicit Text (`@`)** | Memorandum Number (transferred from Monthly) |
| **42** | **AP**| `DI MEMO DATE` | `DD` | `di_memo_date_dd` | Integer (1–31) | Split Date: Day |
| **43** | **AQ**| *Merged with AP1*| `MM` | `di_memo_date_mm` | Integer (1–12) | Split Date: Month |
| **44** | **AR**| *Merged with AP1*| `YYYY` | `di_memo_date_yyyy`| Integer (4-digit) | Split Date: Year |
| **45** | **AS**| *None* | `GOVERNMENT ANALYST`| `govt_analyst` | Text | Analyst Name (Row 1 is None) |
| **46** | **AT**| *None* | `FEES` | `extra_fees` | **Explicit Text** | **PDT Sheet only!** (Row 2 is `'FEES'`, Col 46 absent in DI sheet). |

---

## 4. Ingestion, Validation & Synchronization Pipeline

### 4.1 Legacy SAMPNO Typo Normalization Logic
To handle operator typos like `26DO729[10/IBC]` where `'O'` was entered instead of zero `'0'`:

```python
import re

SAMPNO_RAW_REGEX = re.compile(r"^(\d{2})([A-Z]+)(\d+)(?:\[(.*)\])?$")

def parse_sampno(raw_sampno: str):
    """
    Parses and normalizes SAMPNO strings with typo correction.
    Example: '26DO729[10/IBC]' -> year=2026, group='DI', sample_no=729, raw='26DO729[10/IBC]'
             '26UO1484'        -> year=2026, group='UO', sample_no=1484
    """
    raw_clean = str(raw_sampno).strip()
    match = SAMPNO_RAW_REGEX.match(raw_clean)
    if not match:
        raise ValueError(f"Unrecognized SAMPNO format: {raw_sampno}")
    
    yy_str, group_token, num_str, bracket_suffix = match.groups()
    year = 2000 + int(yy_str)
    
    # Legacy Typo Correction: 'DO' -> 'D' + '0', 'CO' -> 'C' + '0', 'PO' -> 'P' + '0', 'EO' -> 'E' + '0'
    # BUT 'UO' is the valid group code for U.O.
    if group_token in ('DO', 'CO', 'PO', 'EO'):
        prefix = group_token[0]
        group_letter = prefix
        sample_num = int("0" + num_str) # Normalize 'O' to leading zero
    else:
        group_letter = group_token
        sample_num = int(num_str)
        
    group_map = {
        'D': 'DI',
        'DI': 'DI',
        'C': 'CMSO',
        'CMSO': 'CMSO',
        'P': 'PDT',
        'PDT': 'PDT',
        'U': 'UO',
        'UO': 'UO',
        'E': 'ESIS',
        'ESIS': 'ESIS'
    }
    canonical_group = group_map.get(group_letter, group_letter)
    
    # Canonical standardized SAMPNO without brackets
    clean_sampno = f"{yy_str}{group_letter}{sample_num}"
    
    return {
        "sampno": clean_sampno,
        "sampno_raw": raw_clean,
        "year": year,
        "year_prefix": int(yy_str),
        "group_letter": group_letter,
        "group_code": canonical_group,
        "sample_no": sample_num,
        "bracket_suffix": bracket_suffix
    }
```

### 4.2 Row Deletion & Insertion Re-Sequencing Engine
When a row is deleted or inserted in SQLite and Excel, physical row indices shift:

```
[User triggers Delete Row in GUI]
                 │
                 ▼
[Check: Is sample dispatched in Master?]
  ├── Yes ──> [Prompt: "Sample has dispatch record. Delete both or cancel?"]
  │
  ▼ Proceed
[Step 1: Check File Lock on target .xlsx]
  ├── If locked ──> [Raise clean GUI retry prompt]
  │
  ▼ Free
[Step 2: Create Backup in .backups/]
                 │
                 ▼
[Step 3: Modify Excel Sheet via openpyxl]
  - ws.delete_rows(target_excel_row_idx, 1)
  - If Monthly Sheet: Re-calculate and write sequential SR. NO down the column
  - Save to .tmp_<uuid>.xlsx
                 │
                 ▼
[Step 4: Verify Temp File Integrity]
                 │
                 ▼
[Step 5: Atomic os.replace()]
                 │
                 ▼
[Step 6: Update SQLite Database inside Transaction]
  - DELETE FROM monthly_samples WHERE id = :id;
  - UPDATE monthly_samples 
    SET excel_row_idx = excel_row_idx - 1,
        sr_no = sr_no - 1
    WHERE file_name = :file_name 
      AND sheet_name = :sheet_name 
      AND excel_row_idx > :deleted_row_idx;
                 │
                 ▼
[Step 7: Broadcast WebSocket Update to GUI]
```

### 4.3 "Create New Month File" Feature (Workspace 1)
1. **Trigger:** User clicks "+ New Month File" button in Workspace 1.
2. **Input Dialog:** User selects Target Month (e.g. `MAY`) and Year (e.g. `2026`).
3. **Template Cloning:**
   * Backend copies the pure header layout of `APRIL_TEMPLATE.xlsx` to `<WORKSPACE>/MAY 2026.xlsx`.
   * Preserves all 5 sheets (`D.I.`, `CMSO`, `PDT`, `U.O.`, `ESIS`), fonts, column widths, and merged cells.
   * Data rows in all 5 sheets start completely blank (Row 2).
4. **Chronological Auto-Increment Continuity:**
   * Queries SQLite:
     ```sql
     SELECT group_code, COALESCE(MAX(sample_no), 0) AS max_sample 
     FROM monthly_samples 
     WHERE year = :year 
     GROUP BY group_code;
     ```
   * Stores the baseline starting number for each group. When the user enters the first sample in `MAY 2026.xlsx` for tab `D.I.`, `sample_no` automatically suggests `max_sample + 1`.

### 4.4 Workspace Folder Selector & Force Full Re-Scan
1. **Dynamic Workspace Path:**
   * User can click the folder icon in the top chassis header to select any folder on their PC.
   * The path is stored in `app_config('workspace_folder_path')`.
2. **Force Full Re-Scan Engine:**
   * Triggers background re-ingestion of all `.xlsx` files in the selected folder.
   * Compares file modification timestamps and SHA256 hashes to skip unmodified files or selectively re-sync dirty files.
   * Refreshes SQLite cache in <500ms and updates UI LED indicators.

---

## 5. 100% Offline Neo-Skeuomorphic GUI Design Specification

### 5.1 Zero-CDN Design Tokens (`frontend/css/variables.css`)

```css
:root {
  /* Physical Metal Chassis & Framing */
  --chassis-dark: #1b1e24;
  --chassis-metal: #232731;
  --panel-face: #2c313d;
  --panel-bevel-light: rgba(255, 255, 255, 0.09);
  --panel-bevel-dark: rgba(0, 0, 0, 0.65);
  --brushed-aluminum: linear-gradient(145deg, #323846, #242833);

  /* Recessed Wells (Inset Physical Shadows for Data Entry) */
  --well-bg: #15181e;
  --well-border: #111419;
  --well-shadow: inset 2px 2px 5px rgba(0,0,0,0.7), inset -1px -1px 2px rgba(255,255,255,0.05);

  /* Raised Mechanical Push-Buttons */
  --btn-face: linear-gradient(180deg, #3b4252 0%, #2e3440 100%);
  --btn-border: #1d212a;
  --btn-shadow: 0 4px 0 #14171d, 0 6px 12px rgba(0, 0, 0, 0.55);
  --btn-active-shadow: 0 1px 0 #14171d, 0 2px 4px rgba(0, 0, 0, 0.5);

  /* Hardware Status LEDs (Pulsing Glow Effects) */
  --led-amber: #ffaa00;
  --led-amber-glow: 0 0 8px #ffaa00, 0 0 16px rgba(255, 170, 0, 0.6), inset 0 0 3px #fff;

  --led-green: #00e676;
  --led-green-glow: 0 0 8px #00e676, 0 0 16px rgba(0, 230, 118, 0.6), inset 0 0 3px #fff;

  --led-red: #ff3366;
  --led-red-glow: 0 0 8px #ff3366, 0 0 16px rgba(255, 51, 102, 0.6), inset 0 0 3px #fff;

  /* Physical Folder Index Tabs (Color-Coded Sample Groups) */
  --tab-di: #d97706;    /* Amber */
  --tab-cmso: #059669;  /* Emerald */
  --tab-pdt: #2563eb;   /* Cobalt */
  --tab-uo: #7c3aed;    /* Amethyst */
  --tab-esis: #e11d48;  /* Coral */

  /* 100% Offline System Fonts (No External Web Fonts) */
  --font-mono: "Cascadia Code", Consolas, "Courier New", monospace;
  --font-ui: "Segoe UI", -apple-system, BlinkMacSystemFont, Tahoma, sans-serif;
}
```

### 5.2 UI Component Tree & Workspace Navigation

```
DesktopMainWindow
│
├── HardwareChassisHeader (Physical Bevel, Workspace Folder Selector, Status LEDs)
│    ├── FolderPathSelector (Displays active directory, [Browse Folder] button, [Force Re-Scan])
│    ├── SystemStatusIndicator (Hardware LED: Green=Synced, Amber=Syncing, Red=Excel Lock)
│    ├── WorkspaceSwitchbar (4 Tactile 3D Buttons: Arrivals, Dispatch, Tally, Directory)
│    └── GlobalActions (Theme Switcher [Light / Dark Mode], Omni-Search [Ctrl+F], Force Re-Sync [Ctrl+S], Quick Add [Ctrl+N])
│
├── WorkspaceViewport (Dynamic Content Area)
│    │
│    ├── [Workspace 1: Monthly Arrival Register]
│    │    ├── MonthToolbar (Month Selector Tape, [+ New Month File] physical button)
│    │    ├── PhysicalIndexTabs (5 Color-Coded Tabs: D.I., CMSO, PDT, U.O., ESIS)
│    │    ├── RapidEntryWell (Auto-incremented Sample No, Auto-Suggest Inspector & District)
│    │    ├── RecessedDataTable (Grid view, status LED on every row, inline edit, delete with re-sequence)
│    │    └── KeyboardNavigationTraps (Enter: commit/next cell; Tab: traverse; Up/Down: rows)
│    │
│    ├── [Workspace 2: Lab Testing & Master Dispatch Entry]
│    │    ├── SampleLookupConsole (Search by Sample No or Memo No with auto-suggest)
│    │    └── DualConsoleChassis
│    │         ├── LeftPlate: Locked Arrival Plate (Brushed steel plate, read-only badges)
│    │         │    └── Displays: Receive Date, Sample Name, Batch No, Memo, Inspector, Short Mfg
│    │         └── RightPlate: Lab Testing & Dispatch Instrument Console (Active recessed inputs)
│    │              ├── ManufacturerMemoryBlock (Auto-populates Licence, 3 Addresses, Dist/State codes)
│    │              ├── DatePickersCluster (Single clean pickers -> Auto-split to DD/MM/YYYY)
│    │              ├── TestReportMatrix (Col 25-29: 'Q', Quarter, Report No, Year, Group)
│    │              ├── ResultSelector (Tactile toggle: "1 - Standard Quality" vs "2 - NSQ")
│    │              ├── FeesInput (Text well: supports numbers like "1390" or "NIL")
│    │              ├── ARReportBlock (Report No, Split Date, Govt Analyst)
│    │              └── PushSwitch ("COMMIT DISPATCH & SYNC EXCEL" [Raised 3D Button])
│    │
│    ├── [Workspace 3: Multi-File Tally & Reconciliation Engine]
│    │    ├── MetricMeters (Analog-style readouts: Total Arrived, Dispatched, Pending, Mismatched)
│    │    ├── FilterBar (All, Pending Dispatch, Tallied, Orphan Master, Batch Mismatches)
│    │    ├── SideBySideDiffInspector (Visual comparison of Monthly arrival row vs Master row)
│    │    └── OneClickRepairActions (Auto-fill discrepancies, Re-link orphans)
│    │
│    └── [Workspace 4: Master Directories & Lookups]
│         ├── ManufacturerDirectoryView (View/Edit saved manufacturers & 7 formal fields)
│         ├── InspectorDistrictDirectoryView (Manage Inspector aliases & Gujarat District codes)
│         └── ExcelAuditLog (Timestamped log of all Excel reads, writes & backups)
│
└── HardwareStatusBar (Active File Path, Open Handle Count, Pending SQLite Transactions)
```

---

## 6. Implementation Stages & Approval Gate

| Phase | Milestone | Deliverables & Verification Criteria |
| :---: | :--- | :--- |
| **Phase 1** | Virtual Environment & Inspection *(Completed)* | `.venv` created, `openpyxl` & `pandas` verified, schemas mapped. |
| **Phase 2** | Project Skeleton & SQLite Engine | `config.py`, `backend/database.py`, `backend/models.py`, table creation with WAL mode, indexes, and district seeds. |
| **Phase 3** | Lock Detector & Atomic Writer | `backend/excel_lock.py`, `backend/excel_backup.py`, `backend/excel_writer.py` (atomic swap, backup rotation, `@` text enforcement, date splitting). |
| **Phase 4** | Ingestion Engine & Legacy Typo Normalizer | `backend/excel_reader.py` (ESIS shift handling, `26DO729` -> `26D0729` parser, multi-month sequential ingestion). |
| **Phase 5** | Auto-Memory & Reconciliation Engine | `backend/memory_service.py` (7-field manufacturer memory, inspector splitting), `backend/tally_engine.py` (<100ms reconciliation). |
| **Phase 6** | API Routes & New Month Creator | `backend/routes/` (`arrival_routes.py`, `dispatch_routes.py`, `tally_routes.py`, `directory_routes.py`, template cloning). |
| **Phase 7** | 100% Offline Neo-Skeuomorphic GUI | `frontend/` (index.html, variables.css, components.css, workspaces.css, JS modules with physical tabs, LEDs, and keyboard traps). |
| **Phase 8** | Desktop Shell & End-to-End Validation | `main.py` (FastAPI + PyWebView desktop launcher), two-way Excel sync validation, lock collision testing, row re-sequencing verification. |

---

*Document updated and saved in workspace as `IMPLEMENTATION_PLAN.md`.*
