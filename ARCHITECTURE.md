# Architecture

## Overview

Warehouse Master is a desktop application for printing numbered PDF labels and tracking laptop reassembly via Google Sheets. Two independent tabs: Labels (PDF generation) and Reassembly (Google Sheets sync).

## File structure

| File | Purpose |
|------|---------|
| **main.py** | Entry point, `LabelApp` main window, tab lifecycle, i18n dispatch |
| **printing.py** | Utilities: file I/O, resource paths, printer discovery, app config folder |
| **styles.py** | Stylesheet builder: `build_stylesheet(dark: bool)` → returns CSS for both themes |
| **workers.py** | Background threads: `PDFWorker` (reportlab), `ReassemblyWorker` (gspread sync) |
| **widgets.py** | Reusable UI: `NoScrollComboBox`, `RangeRowWidget`, `PreferencesDialog` |
| **strings.py** | i18n: `STRINGS` dict `{"en": {...}, "ru": {...}}` with all UI strings |
| **sheet_manager.py** | Google Sheets API wrapper: config-driven column indices, category calculation, batch updates |
| **sheet_config.example.json** | Template config: worksheets, column mappings, translators, statuses |
| **WarehouseMaster.spec** | PyInstaller spec: bundles `Inter.ttf`, builds single-file exe |
| **requirements.txt** | Dependencies: PyQt5, reportlab, gspread, google-auth |

## Module responsibilities

### main.py
- Loads/saves QSettings (theme, language, window state)
- Renders two tabs: labels and reassembly
- Wires up event handlers
- Calls `_retranslate()` on locale change
- Temp file cleanup on close

### printing.py
- `resource_path()` — finds bundled files (Inter.ttf, icon.ico)
- `app_data_dir()` — `%APPDATA%/WarehouseMaster/` for token.json, local configs
- `config_path()` — returns sheet_config.json (local or appdata)
- `register_fonts()` — loads Inter.ttf into reportlab
- `get_installed_printers()` — enumerates Windows printers (win32api)
- `open_file()` — cross-platform file open (Windows/macOS/Linux)
- `print_file()` — print to specific printer or system default

### styles.py
- `build_stylesheet(dark: bool)` — single function, returns full QPalette CSS
- Colors hardcoded (dark: #212529 bg, #f8f9fa text; light: inverse)
- Called on theme toggle → `setStyleSheet()`

### workers.py
- `PDFWorker(QThread)` — generates PDF in background, emits `finished(filepath)` or `error_occurred(str)`
- `ReassemblyWorker(QThread)` — calls `SheetManager.process_reassembly()`, emits `finished_signal(comment, tech_op)` or `error_signal(str)`
- Both prevent UI freeze

### widgets.py
- `NoScrollComboBox` — suppresses scroll-wheel zoom
- `RangeRowWidget` — start/end inputs + +/- buttons; callback-driven
- `PreferencesDialog` — language + theme + sheet URL + save folder, saves to QSettings

### strings.py
- Two dicts: `STRINGS["en"]`, `STRINGS["ru"]`
- Keys: `"window_title"`, `"tab_labels"`, message templates with `{n}` placeholders
- No locale switching logic — main.py reads `settings.value("locale")` and indexes

### sheet_manager.py
- `SheetManager(sheet_url, config_path)` — loads config.json, authorizes gspread
- `process_reassembly(laptop_id, parts_str, ssd_id, akb_id)` — atomically updates: marks parts shipped, writes grades to laptop row, recalculates category (D/C/B/A/NEW)
- `_calculate_category(laptop_data)` — rule-based scoring (D if any part ≤rank 1, NEW if all ≥A and cycles < 150, etc.)
- Config-driven: all column indices, range clears, status values from sheet_config.json

## Hot paths

### PDF generation
1. User clicks "Generate PDF"
2. `_start_generation()` validates ranges (start ≤ end), spawns `PDFWorker`
3. `PDFWorker.run()` → `reportlab.canvas` draws labels in grid layout
4. On success: `_on_pdf_done()` → open file or print
5. UI unblocked (worker thread)

### Reassembly sync
1. User fills order/parts, clicks "Apply changes"
2. `_run_reassembly()` spawns `ReassemblyWorker`
3. `ReassemblyWorker.run()` → `SheetManager.process_reassembly()`
4. Manager: fetches IDs from all worksheets, processes each part (SSD/battery/part), calculates new category
5. Batch updates all sheets, returns comment + tech lines
6. `_on_reassembly_done()` displays results
7. UI unblocked

## Adding things

### New label format (e.g., 6×6 grid)
1. Add to `PAGE_SIZES` and `DEFAULT_FONT_SIZES` in workers.py
2. Add radio button in `_init_gen_tab()`
3. Add branch in `PDFWorker.run()` for grid layout

### New reassembly field
1. Add config key to sheet_config.example.json (e.g., `"warranty_months": 52`)
2. Read in `SheetManager.__init__()` via self.cfg
3. Add processing in `_process_part()` or new `_process_<thing>()` method

### New language
1. Add `STRINGS["new_lang"]` dict in strings.py
2. Add to language combo in PreferencesDialog (widgets.py)
3. Map combo index → locale code (e.g., index 2 → "de")

### New Google Sheets worksheet
1. Add to `sheet_config.json` → `worksheets`
2. Add column mappings if needed
3. Add fetch/batch in `SheetManager` methods
4. Wire up in `process_reassembly()`

## Gotchas

- **QSettings casing:** Linux filenames are case-sensitive; use lowercase keys (`"sheet_url"` not `"SheetURL"`)
- **Token refresh:** If gspread credentials expire mid-session, worker will fail; user must restart and re-auth
- **Column alignment:** reportlab canvas Y-axis is bottom-up (0 = bottom). Grid layout offsets Y correctly with `ph - (row + 1) * cell_h`
- **Config missing:** If sheet_config.json missing, SheetManager raises on init; handle in UI with try-except, show user-friendly message
- **Cyrillic grades:** Before rank check, normalize Cyrillic А/В/С/Д → Latin A/B/C/D via `str.maketrans()`
- **Printer not found:** If saved printer deleted, `findText()` returns -1; guard before `setCurrentIndex()`
- **Temp files:** If app crashes, temp PDFs not deleted; consider OS-level temp cleanup (tmp dirs auto-purge)
