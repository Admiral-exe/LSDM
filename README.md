<div align="center">

<img src="assets/logo.png" alt="LSDM Logo" width="128" height="128" style="border-radius: 24px; box-shadow: 0 8px 24px rgba(6,182,212,0.35);" />

# LSDM (Lab Supply & Dispatch Manager)
### Desktop Laboratory Sample & Supply Chain Management System

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](version.py)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/database-SQLite%20WAL-003B57.svg)](https://www.sqlite.org/)
[![Windows](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078D6.svg)](https://www.microsoft.com/)
[![Offline](https://img.shields.io/badge/network-100%25%20Offline-success.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*An offline-first, native Windows desktop application for pharmaceutical and chemical analytical laboratories, featuring high-speed data capture, auto-learning manufacturer/inspector memory, and two-way atomic Excel synchronization.*

</div>

---

## 🌟 Key Highlights

- **100% Offline-First**: Zero cloud dependencies, zero external CDNs, zero telemetry. All assets, fonts, icons, and SQLite data engines run locally on the client's machine.
- **Native Windows Desktop Experience**: Embedded Microsoft Edge WebView2 shell with native desktop windowing, hardware chassis header, and dark/light themes.
- **Two-Way Atomic Excel Sync**: Ingests, normalizes, and writes directly to active laboratory workbooks (`APRIL_TEMPLATE.xlsx`, `Master 2026.xlsx`) with automated `.backups` before every disk modification.
- **Auto-Learning Intelligence**: Remembers drug manufacturers, addresses, default district allocations, inspector assignments, and sample code mappings automatically as staff enters data.
- **One-Click In-Place Upgrades**: Client installations can be updated anytime by distributing a new setup file. User databases, configurations, and Excel templates are **strictly preserved** during upgrades.

---

## 🏗️ Architecture & Modules

```
                           +---------------------------+
                           |   Desktop Window Shell    |
                           |   (Edge Chromium Native)  |
                           +-------------+-------------+
                                         |
                                         v
+-----------------------+  HTTP / WS   +-----------------------+   Read/Write   +-----------------------+
|  Local HTML/JS/CSS    | <==========> |   FastAPI Local Host  | <============> |  SQLite WAL Engine    |
|  Hardware UI Chassis  |              |   (127.0.0.1:8765)    |                |  supply_management.db |
+-----------------------+              +-----------+-----------+                +-----------+-----------+
                                                   |                                        |
                                                   | Atomic Sync                            | Periodic
                                                   v                                        v
                                       +-----------------------+                +-----------------------+
                                       |  Excel Workbooks      |                |  Automated Snapshots  |
                                       |  Monthly & Master     |                |  .backups/ directory  |
                                       +-----------------------+                +-----------------------+
```

### 1. Monthly Arrivals (Workspace 1)
- Continuous data entry for newly arriving drug/chemical samples.
- Auto-increments serial numbers and computes official laboratory sample codes.
- Pre-fills inspector details and district codes upon inspector selection.
- Real-time row insertion into active monthly spreadsheets.

### 2. Master Dispatch & Lab Testing (Workspace 2)
- One-click sample transfer from Monthly Arrivals to Master Testing Dispatches.
- Auto-resolves sample group routing (`DI`, `CMSO`, `PDT`, `UO`, `ESIS`).
- Corrects legacy typo patterns (e.g., `DO` $\rightarrow$ `DI`, `CO` $\rightarrow$ `CMSO`).
- Automatically splits dispatch dates into Day, Month, and Year components for Excel matrix compliance.

### 3. Tally & Cross-Workbook Reconciliation (Workspace 3)
- Reconciles Monthly Arrival logs against Master Dispatch sheets in real time.
- Identifies pending tests, missing entries, date mismatches, and orphan dispatches.
- One-click discrepancy resolution and export.

### 4. Memory & Central Directories (Workspace 4)
- District lookup table for Gujarat state territories (Codes 1 through 18).
- Drug Inspector directory with default jurisdiction mappings.
- Manufacturer directory with auto-aliasing and smart auto-complete.

---

## 📦 For Clients: Installation & Updates

### First-Time Installation
1. Provide the client with the installer file: **`LSDM_Setup_v1.0.0.exe`**.
2. The client double-clicks the setup file.
3. The setup wizard installs LSDM into the user's application directory (`%LOCALAPPDATA%\Programs\LSDM`) — **no administrative permissions required**.
4. A desktop shortcut with the LSDM minimal logo is automatically created.
5. Launch **LSDM** from the Desktop or Start Menu.

### Updating to a Newer Version
When you release changes or new features:
1. Update version in `version.py` (e.g., to `1.0.1`).
2. Run `build_installer.bat` to generate **`LSDM_Setup_v1.0.1.exe`**.
3. Send the new setup file to the client.
4. When the client runs the installer, it detects the existing installation:
   - **Binaries & application logic are updated**.
   - **Database (`supply_management.db`) is NEVER overwritten**.
   - **Existing configurations, directories, and workspace paths are retained intact**.

---

## 🛠️ For Developers: Setup & Building

### 1. Local Development Setup
```bash
# Clone the repository
git clone https://github.com/your-username/LSDM.git
cd LSDM

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python main.py
```

### 2. Building the Standalone EXE and Installer
The automated pipeline compiles `LSDM.exe` via PyInstaller and creates the single-file setup wizard via Inno Setup:

```bash
# Simply run the automated build script:
build_installer.bat
```

The resulting setup wizard will be created at:
```
dist_installer\LSDM_Setup_v1.0.0.exe
```

---

## 🏷️ Centralized Versioning

Version numbers are controlled from a single source of truth: [`version.py`](version.py).

```python
__version__ = "1.0.0"
__app_name__ = "LSDM"
__full_name__ = "Laboratory Sample & Dispatch Management System"
__build_date__ = "2026-10-17"
```

The version is automatically:
- Rendered in the desktop application window title bar.
- Displayed in the top hardware chassis UI badge (`#app-version-badge`).
- Served via API at `/api/version`.
- Embedded into the Windows `.exe` metadata and Inno Setup installer package.

---

## 📁 Repository Structure

```
LSDM/
│── assets/                  # High-DPI Windows icons and logo assets
│   ├── logo.ico             # Multi-resolution icon (16x16 to 256x256)
│   └── logo.png             # 512x512 master logo graphic
│── backend/                 # FastAPI REST API & Core Services
│   ├── routes/              # Workspace endpoint routers
│   ├── database.py          # SQLite schema, connection pool & WAL config
│   ├── excel_reader.py      # Spreadsheet parser & typo correction engine
│   ├── excel_writer.py      # Atomic Excel writer with backup snapshots
│   ├── memory_service.py    # Auto-learning directory memory
│   └── models.py            # Pydantic schemas and validation
│── frontend/                # Offline UI (Zero CDNs, 100% Local)
│   ├── css/                 # Modern chassis stylesheets (Dark/Light)
│   ├── js/                  # Vanilla JS workspace controllers
│   ├── index.html           # Main UI entry point
│   └── favicon.ico          # Browser tab icon
│── tools/                   # Helper scripts
│   └── generate_logo.py     # Logo and icon generation script
│── APRIL_TEMPLATE.xlsx      # Master Monthly Arrival Excel template
│── MASTER_TEMPLATE.xlsx     # Master Testing Dispatch Excel template
│── config.py                # Environment & runtime configuration
│── version.py               # Central version registry
│── main.py                  # Desktop application entry point
│── lsdm.spec                # PyInstaller compilation specification
│── installer.iss            # Inno Setup installation wizard configuration
│── build_installer.bat      # One-click build and packaging batch script
│── requirements.txt         # Pinned Python package dependencies
│── .gitignore               # Clean Git exclusion rules
│── LICENSE                  # MIT License
└── README.md                # Documentation
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
