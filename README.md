[Русский](README.ru.md)

# Warehouse Master

Desktop utility for printing numbered labels as PDF and updating a Google Sheets inventory when reassembling laptops.

```
python main.py
```

## Install

Requirements: Python 3.10+, Windows/macOS/Linux.

```
pip install -r requirements.txt
```

## What it does

**Labels tab** — generate a PDF of sequentially numbered labels in three formats:

| Format | Page size | Labels per page |
|--------|-----------|-----------------|
| Single | 58×40 mm landscape | 1 |
| Grid 2×2 | 58×40 mm | 4 |
| Grid 4×4 | 120×75 mm | 16 |

Enter one or more number ranges, pick a font size, and click Generate PDF. Enable Auto-print to send directly to a printer. Temporary mode deletes the file when the app closes.

**Reassembly tab** — record which parts were installed in a laptop. Looks up each part ID in a Google Sheet, marks it as shipped, writes the grade to the laptop row, and recalculates the laptop category (NEW/A/B/C/D). Outputs a ready-to-paste comment and tech operation text.

## Google Sheets setup

1. Create a Google Cloud project and enable the Sheets API.
2. Create an OAuth 2.0 Desktop client and download `credentials.json`.
3. Place `credentials.json` next to `main.py` (or in `%APPDATA%/WarehouseMaster/`).
4. Copy `sheet_config.example.json` to `sheet_config.json` and edit it to match your spreadsheet structure (worksheet names, column indices, status values).
5. Open Settings and paste the spreadsheet URL.

On first run the browser will open for OAuth consent; the token is stored in `%APPDATA%/WarehouseMaster/token.json`.

## For developers

Stack: Python 3.10, PyQt5, reportlab, gspread, google-auth.

```
# run from source
python main.py

# build standalone exe (Windows)
pyinstaller WarehouseMaster.spec
```

`Inter.ttf` is licensed under the SIL Open Font License 1.1.

## License

MIT
