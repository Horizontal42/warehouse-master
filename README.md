[Русский](README.ru.md)

# Warehouse Master

> Enterprise Service Center WMS, Hardware Refurbishment Tracking & Industrial Label Printing System

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Engine](https://img.shields.io/badge/PDF%20Engine-ReportLab-orange.svg)](https://www.reportlab.com/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/Horizontal42/warehouse-master)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Warehouse Master is a specialized desktop Warehouse Management System (WMS) and refurbishment tracking suite engineered for electronics service centers, warranty repair hubs, and hardware refurbishment lines. The platform automates component tracking, drives a multi-factor algorithmic hardware grading engine (classifying reconditioned units into NEW, A, B, C, and D tiers), provides high-throughput stream generation of serialized thermal barcode labels via ReportLab, and synchronizes real-time inventory states with a centralized cloud database via the Google Sheets API.

By automating manual stock reconciliation, component-to-chassis binding, and thermal label generation, Warehouse Master significantly accelerates workstation throughput, reduces technician assembly errors, and maintains an auditable chain of custody across thousands of serialized components.

---

## Key Capabilities

### 1. Algorithmic Hardware Grading Engine (NEW / A / B / C / D)
Automates objective quality grading of assembled laptops and electronics through rule-based scoring across structural components, sub-assemblies, and telemetry attributes:
- **Component Factor Evaluation**: Evaluates top cover (A), display bezel (B), palmrest/top case (C1/C2), bottom cover (D), keyboard, trackpad sensors, and display matrix purity.
- **Telemetry Thresholds**: Integrates SSD health metrics (`smartctl` wear / power-on hours) and battery cycle counters.
- **Deterministic Grading Hierarchy**:
  - **NEW (Mint / Pristine)**: Flawless cosmetic sub-assemblies (rank 5/5 on casing and display), battery wear `< 150` cycles, and zero cosmetic defects.
  - **Grade A (Corporate Premium)**: Minor cosmetic wear, premium structural integrity, SSD telemetry Grade A/B, high battery retention.
  - **Grade B (Standard Operational)**: Moderate exterior scuffs, fully functional internal sub-assemblies, SSD telemetry Grade B.
  - **Grade C (Budget / Functional)**: Visible cosmetic defects, higher component wear, fully functional computing core.
  - **Grade D (Salvage / Heavy Wear)**: Any critical structural defect or worn sub-assembly (rank ≤ 1).

### 2. High-Throughput Stream Label & Barcode Generation (ReportLab)
Engineered for industrial thermal roll and sheet label printers:
- **Vector Composition**: Sub-millimeter vector layout rendering via ReportLab with bundled high-legibility typography (`Inter` variable font).
- **Industrial Label Presets**:
  - **Single Roll Label**: `58 × 40 mm` landscape (standard industrial thermal roll size for Zebra, TSC, Godex, Xprinter).
  - **Grid 2 × 2**: `58 × 40 mm` (4 micro-labels per thermal sticker).
  - **Grid 4 × 4**: `120 × 75 mm` (16 serial stickers per sheet format).
- **Range Serialization**: Automatic sequence expansion from start/end ranges (e.g. `1000–1250`), multi-range batching, and instantaneous stream compilation to PDF.
- **Direct Thermal Spooling**: Native integration with the Windows Print Spooler (`win32print`) for one-click background printing without intermediate PDF reader dialogues, plus temporary print job auto-cleanup.

### 3. Cloud WMS & Reassembly Synchronization
- **Atomic Inventory Binding**: Maps disassembled components (system boards, display panels, keyboards, batteries, SSDs) to target laptop chassis IDs.
- **Two-Way Status Reconciliation**: Queries cloud inventory via `gspread`, transitions consumed parts from `In Stock` to `Shipped` (`Отгружен`), clears allocated component bins, and updates master asset records in atomic batch transactions.
- **Audit Logging & ERP Notes**: Automatically compiles standardized technician dispatch notes, bill-of-materials (BOM) summaries, and technical operation logs ready for pasting into external ERP/CRM systems.

### 4. Industrial Ergonomics & Multi-Language Support
- **Dual High-Contrast Themes**: Dark and Light themes styled via custom Qt palettes for warehouse, bench, and cleanroom lighting conditions.
- **No-Scroll Controls**: Specialized UI widgets (`NoScrollComboBox`) designed to eliminate accidental value modifications from mouse wheel scrolling during fast data entry.
- **Full Internationalization**: Built-in runtime switching between English and Russian locales.

---

## Technical Architecture

```
+-------------------------------------------------------------------------------+
|                           Warehouse Master Runtime GUI                        |
|                     (PyQt5 / QSettings / Custom Themes)                       |
+---------------------------------------+---------------------------------------+
                   |                                                 |
                   v                                                 v
+---------------------------------------+ +-------------------------------------+
|        Labels Generator Subsystem     | |       WMS Reassembly Subsystem      |
|                                       | |                                     |
|  - Range Parser & Serial Validator    | |  - Component ID & Barcode Parser    |
|  - ReportLab Vector Canvas Engine     | |  - Multi-Factor Grading Classifier  |
|  - Layout Modes (Single / 2x2 / 4x4)  | |  - Parts Reconciliation Engine      |
|  - Spooler Direct Print (win32print)  | |  - Audit & ERP Comment Generator    |
+---------------------------------------+ +-------------------------------------+
                   |                                                 |
                   v                                                 v
+---------------------------------------+ +-------------------------------------+
|          PDFWorker (QThread)          | |      ReassemblyWorker (QThread)     |
|   Non-blocking background rendering   | |   Non-blocking gspread cloud sync   |
+---------------------------------------+ +-------------------------------------+
                                                                     |
                                                                     v
                                          +-------------------------------------+
                                          |          Google Sheets API          |
                                          |   - Batch Row Upsert                |
                                          |   - Atomic Stock State Transition   |
                                          +-------------------------------------+
```

---

## System Requirements

- **OS**: Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+)
- **Python**: 3.10+
- **Printers Supported**: Any standard Windows-compatible thermal label printer (Zebra, TSC, Godex, Xprinter, Citizen, Brother) or standard laser/inkjet printer.

---

## Installation & Setup

### 1. Repository Setup

```bash
git clone https://github.com/Horizontal42/warehouse-master.git
cd warehouse-master
pip install -r requirements.txt
```

### 2. Google Sheets API Configuration

1. In Google Cloud Console, enable the **Google Sheets API**.
2. Create an **OAuth 2.0 Desktop Client ID** and download the credentials.
3. Place `credentials.json` in the application directory or `%APPDATA%/WarehouseMaster/credentials.json`:

```bash
cp credentials.example.json credentials.json
```

4. Duplicate and adapt the spreadsheet schema configuration:

```bash
cp sheet_config.example.json sheet_config.json
```

### 3. Application Preferences

Launch the application:

```bash
python main.py
```

Navigate to **Settings** (`PreferencesDialog`):
- Configure your cloud spreadsheet URL.
- Select UI theme (Dark / Light) and locale (English / Русский).
- Set default output path for compiled label PDFs.

---

## Production Build

To compile a standalone, single-file Windows executable:

```bash
pyinstaller WarehouseMaster.spec
```

The resulting executable will be created in `dist/WarehouseMaster.exe`.

---

## Configuration Reference (`sheet_config.json`)

The declarative JSON config dictates how the WMS interacts with cloud storage:
- `worksheets`: Maps logical entity types (`laptops`, `parts`, `ssd`, `batteries`) to sheet tab names.
- `laptop_columns`: 1-indexed column indices for laptop attributes, grading outputs, and assigned sub-assemblies.
- `clear_ranges`: A1-notation ranges cleared when a component is unassigned or swapped.
- `type_translator`: Normalizes barcode scan strings and sub-assembly labels to canonical component keys.
- `ssd_grade_thresholds`: Power-on hour boundaries for SSD health classifications.

---

## Security & Privacy

- **Safe Credential Handling**: Local user tokens (`token.json`), client OAuth secrets (`credentials.json`), service keys, and private configuration files are strictly ignored via `.gitignore`.
- **Zero Cloud Leakage**: Authentication tokens are stored locally in the OS secure app data directory (`%APPDATA%/WarehouseMaster/`).

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
Typography: `Inter.ttf` is licensed under the [SIL Open Font License 1.1](http://scripts.sil.org/OFL).
