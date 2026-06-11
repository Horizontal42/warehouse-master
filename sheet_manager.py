from __future__ import annotations

import json
import os

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from printing import app_data_dir, resource_path

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_REQUIRED_CONFIG_KEYS = {
    "worksheets", "laptop_columns", "clear_ranges",
    "type_translator", "sort_order", "statuses", "part_columns",
}

# Cyrillic homoglyphs that look like Latin grade letters
_GRADE_NORM = str.maketrans("АВСД", "ABCD")


def _token_path() -> str:
    return os.path.join(app_data_dir(), "token.json")


def _find_credentials() -> str:
    local = resource_path("credentials.json")
    if os.path.exists(local):
        return local
    appdata = os.path.join(app_data_dir(), "credentials.json")
    if os.path.exists(appdata):
        return appdata
    raise FileNotFoundError(
        "credentials.json not found next to the app or in %APPDATA%/WarehouseMaster/"
    )


class SheetManager:
    def __init__(self, sheet_url: str, config_path: str = "sheet_config.json"):
        self.sheet_url = sheet_url
        self.cfg = self._load_config(config_path)
        self.client = None
        self.doc = None
        self._authorize()

    def _load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Sheet config not found: {path}")
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        missing = _REQUIRED_CONFIG_KEYS - set(cfg)
        if missing:
            raise ValueError(f"sheet_config.json missing keys: {missing}")
        return cfg

    def _authorize(self) -> None:
        token = _token_path()
        creds = None
        if os.path.exists(token):
            try:
                creds = Credentials.from_authorized_user_file(token, SCOPES)
            except Exception:
                os.remove(token)
                creds = None
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                os.remove(token)
                creds = None
        if not creds or not creds.valid:
            creds_file = _find_credentials()
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token, "w") as f:
                f.write(creds.to_json())
        self.client = gspread.authorize(creds)
        self.doc = self.client.open_by_url(self.sheet_url)

    def _get_rank(self, grade_str: str) -> int:
        gs = str(grade_str).strip().upper().translate(_GRADE_NORM)
        if "NEW" in gs:
            return 5
        if "A" in gs:
            return 4
        if "B" in gs:
            return 3
        if "C" in gs:
            return 2
        if "D" in gs:
            return 1
        return 5

    def _calculate_category(self, laptop_data: list) -> str:
        col = self.cfg["laptop_columns"]
        parts_cols = col["parts"]

        def part_rank(key: str) -> int:
            cols = parts_cols.get(key)
            if not cols:
                return 5
            c = cols[0]
            if c - 1 >= len(laptop_data):
                return 5
            val = laptop_data[c - 1]
            if key == "SSD":
                return 1 if not val else self._get_rank(str(val).split("/")[0])
            return 5 if not val else self._get_rank(val)

        grade_keys = ["A", "B", "B1", "C1", "C2", "D", "Клавиатура", "Кнопки", "Сенсор", "Дисплей", "SSD"]
        parts = {k: part_rank(k) for k in grade_keys}

        try:
            cyc_raw = laptop_data[col["battery_cycles"] - 1]
            cycles = int(str(cyc_raw).strip()) if cyc_raw else 9999
        except (ValueError, IndexError):
            cycles = 9999

        if any(r <= 1 for r in parts.values()):
            return "D"

        is_new = (
            parts["B1"] == 5
            and parts["Клавиатура"] == 5
            and parts["Дисплей"] == 5
            and all(v >= 4 for k, v in parts.items() if k not in ("B1", "Клавиатура", "Дисплей"))
            and cycles < 150
        )
        if is_new:
            return "NEW"

        if parts["B"] >= 3 and all(v >= 4 for k, v in parts.items() if k != "B"):
            return "A"

        if (
            parts["D"] >= 2
            and parts["SSD"] >= 2
            and all(v >= 3 for k, v in parts.items() if k not in ("D", "SSD"))
        ):
            return "B"

        return "C" if all(v >= 2 for v in parts.values()) else "D"

    def _fetch_initial_data(self) -> tuple[list, list, list, list, list]:
        ws = self.cfg["worksheets"]
        parts_range = self.cfg.get("parts_data_range", "G:K")
        fetched = self.doc.values_batch_get([
            f"{ws['laptops']}!A:A",
            f"{ws['parts']}!A:A",
            f"{ws['ssd']}!A:A",
            f"{ws['batteries']}!A:A",
            f"{ws['parts']}!{parts_range}",
        ])
        vr = fetched["valueRanges"]

        def ids(i):
            return [row[0] if row else "" for row in vr[i].get("values", [])]

        return ids(0), ids(1), ids(2), ids(3), vr[4].get("values", [])

    def _load_laptop_row(self, ws_laptops, laptop_row: int) -> list:
        col = self.cfg["laptop_columns"]
        all_indices = (
            [col["serial"], col["warehouse"], col["status"], col["category"],
             col["ssd"], col["battery_cycles"], col["battery_capacity"]]
            + [c for cols in col["parts"].values() for c in cols]
        )
        max_col = max(all_indices)
        end_col = gspread.utils.rowcol_to_a1(1, max_col).rstrip("0123456789")
        data = ws_laptops.get(f"A{laptop_row}:{end_col}{laptop_row}")[0]
        while len(data) < max_col:
            data.append("")
        return data

    def _process_ssd(self, ssd_id: str, ids_ssd: list, ws_ssd, laptop_row: int,
                     laptop_data: list, batches: dict, collected: list, errors: list) -> None:
        try:
            idx = ids_ssd.index(str(ssd_id))
            row = idx + 1
            pc = self.cfg["part_columns"]
            st = self.cfg["statuses"]
            fields = self.cfg.get("ssd_data_fields", {"code": 0, "hours": 6, "cycles": 7})
            sc, ec = self.cfg.get("ssd_data_range", "G:N").split(":")

            batches["ssd"].append({"range": f"{pc['ssd_availability']}{row}", "values": [[st["in_stock_no"]]]})
            batches["ssd"].append({"range": f"{pc['ssd_status']}{row}", "values": [[st["shipped"]]]})

            data = ws_ssd.get(f"{sc}{row}:{ec}{row}")[0]
            code = data[fields["code"]] if fields["code"] < len(data) else "?"
            hours = data[fields["hours"]] if fields["hours"] < len(data) else "?"
            cycles = data[fields["cycles"]] if fields["cycles"] < len(data) else "?"

            thr = self.cfg.get("ssd_grade_thresholds", {"a_max_hours": 1000, "b_max_hours": 15000})
            try:
                h = int(str(hours).replace("ч", "").strip())
                sg = "A" if h < thr["a_max_hours"] else ("B" if h < thr["b_max_hours"] else "C")
            except (ValueError, TypeError):
                sg = "B"

            info = f"{sg}/{hours}/{cycles}"
            c_idx = self.cfg["laptop_columns"]["ssd"]
            old_val = laptop_data[c_idx - 1]
            batches["laptops"].append({
                "range": gspread.utils.rowcol_to_a1(laptop_row, c_idx),
                "values": [[info]],
            })
            laptop_data[c_idx - 1] = info

            collected.append({
                "type": "SSD",
                "report": f"SSD {ssd_id} ({info})",
                "tech": f"SSD: Code {code}, ID {ssd_id}, {sg} ({hours}h) (was: {old_val})",
            })
        except ValueError:
            errors.append(f"SSD {ssd_id} not found")

    def _process_battery(self, akb_id: str, ids_akb: list, ws_akb, laptop_row: int,
                         laptop_data: list, batches: dict, collected: list, errors: list) -> None:
        try:
            idx = ids_akb.index(str(akb_id))
            row = idx + 1
            pc = self.cfg["part_columns"]
            st = self.cfg["statuses"]
            fields = self.cfg.get("battery_data_fields", {"code": 0, "cycles": 2, "capacity": 3})
            sc, ec = self.cfg.get("battery_data_range", "I:L").split(":")

            batches["batteries"].append({"range": f"{pc['battery_availability']}{row}", "values": [[st["in_stock_no"]]]})
            batches["batteries"].append({"range": f"{pc['battery_status']}{row}", "values": [[st["shipped"]]]})

            data = ws_akb.get(f"{sc}{row}:{ec}{row}")[0]
            code = data[fields["code"]] if fields["code"] < len(data) else "?"
            cyc = data[fields["cycles"]] if fields["cycles"] < len(data) else "?"
            cap = data[fields["capacity"]] if fields["capacity"] < len(data) else "?"

            col = self.cfg["laptop_columns"]
            old_cyc = laptop_data[col["battery_cycles"] - 1]
            batches["laptops"].append({
                "range": gspread.utils.rowcol_to_a1(laptop_row, col["battery_cycles"]),
                "values": [[cyc]],
            })
            batches["laptops"].append({
                "range": gspread.utils.rowcol_to_a1(laptop_row, col["battery_capacity"]),
                "values": [[cap]],
            })
            laptop_data[col["battery_cycles"] - 1] = cyc
            laptop_data[col["battery_capacity"] - 1] = cap

            collected.append({
                "type": "АКБ",
                "report": f"Battery {akb_id} ({cyc} cycles)",
                "tech": f"Battery: Code {code}, ID {akb_id}, {cyc} cycles (was: {old_cyc})",
            })
        except ValueError:
            errors.append(f"Battery {akb_id} not found")

    def _process_part(self, p_id: str, ids_parts: list, parts_data: list, ws_parts,
                      laptop_row: int, laptop_data: list, batches: dict,
                      clear_ranges: list, collected: list, errors: list) -> None:
        try:
            idx = ids_parts.index(str(p_id))
            row = idx + 1
            pc = self.cfg["part_columns"]
            st = self.cfg["statuses"]
            fields = self.cfg.get("parts_data_fields", {"type": 0, "grade": 2, "code": 3})

            if idx < len(parts_data):
                raw_row = parts_data[idx]
            else:
                sc, ec = self.cfg.get("parts_data_range", "G:K").split(":")
                raw_row = ws_parts.get(f"{sc}{row}:{ec}{row}")[0]

            raw_type = raw_row[fields["type"]] if fields["type"] < len(raw_row) else "?"
            grade = raw_row[fields["grade"]] if fields["grade"] < len(raw_row) else "?"
            code = raw_row[fields["code"]] if fields["code"] < len(raw_row) else "?"

            batches["parts"].append({"range": f"{pc['parts_availability']}{row}", "values": [[st["in_stock_no"]]]})
            batches["parts"].append({"range": f"{pc['parts_status']}{row}", "values": [[st["shipped"]]]})

            internal_type = self.cfg["type_translator"].get(raw_type)
            if not internal_type:
                for key, val in self.cfg["type_translator"].items():
                    if key in raw_type:
                        internal_type = val
                        break

            display_type = internal_type or raw_type
            old_val = "?"

            if internal_type:
                target_cols = self.cfg["laptop_columns"]["parts"].get(internal_type, [])
                for c_idx in target_cols:
                    old_val = laptop_data[c_idx - 1]
                    batches["laptops"].append({
                        "range": gspread.utils.rowcol_to_a1(laptop_row, c_idx),
                        "values": [[grade]],
                    })
                    laptop_data[c_idx - 1] = grade

                clear_rng = self.cfg["clear_ranges"].get(internal_type)
                if clear_rng:
                    sc, ec = clear_rng.split(":")
                    clear_ranges.append(f"{sc}{laptop_row}:{ec}{laptop_row}")

            collected.append({
                "type": display_type,
                "report": f"{display_type} {p_id}",
                "tech": f"{display_type}: Code {code}, ID {p_id}, {grade} (was: {old_val})",
            })
        except ValueError:
            errors.append(f"Part {p_id} not found")
        except Exception as e:
            errors.append(f"Error processing part {p_id}: {e}")

    def _write_batches(self, ws: dict, batches: dict, clear_ranges: list) -> None:
        if batches["parts"]:
            ws["parts"].batch_update(batches["parts"])
        if batches["ssd"]:
            ws["ssd"].batch_update(batches["ssd"])
        if batches["batteries"]:
            ws["batteries"].batch_update(batches["batteries"])
        if batches["laptops"]:
            ws["laptops"].batch_update(batches["laptops"])
        if clear_ranges:
            ws["laptops"].batch_clear(clear_ranges)

    def process_reassembly(
        self, laptop_id: str, parts_str: str, ssd_id: str, akb_id: str
    ) -> tuple[str, list[str], list[str]]:
        ids_laptops, ids_parts, ids_ssd, ids_akb, parts_data = self._fetch_initial_data()

        try:
            laptop_row = ids_laptops.index(str(laptop_id)) + 1
        except ValueError:
            raise ValueError(f"Laptop {laptop_id} not found")

        cfg_ws = self.cfg["worksheets"]
        ws = {
            "laptops": self.doc.worksheet(cfg_ws["laptops"]),
            "parts": self.doc.worksheet(cfg_ws["parts"]),
            "ssd": self.doc.worksheet(cfg_ws["ssd"]),
            "batteries": self.doc.worksheet(cfg_ws["batteries"]),
        }

        laptop_data = self._load_laptop_row(ws["laptops"], laptop_row)
        serial = laptop_data[self.cfg["laptop_columns"]["serial"] - 1]

        batches: dict[str, list] = {"laptops": [], "parts": [], "ssd": [], "batteries": []}
        clear_ranges: list[str] = []
        collected: list[dict] = []
        errors: list[str] = []

        if ssd_id:
            self._process_ssd(ssd_id, ids_ssd, ws["ssd"], laptop_row, laptop_data, batches, collected, errors)
        if akb_id:
            self._process_battery(akb_id, ids_akb, ws["batteries"], laptop_row, laptop_data, batches, collected, errors)
        if parts_str:
            p_ids = [x.strip() for x in parts_str.replace(",", " ").split() if x.strip()]
            for p_id in p_ids:
                self._process_part(
                    p_id, ids_parts, parts_data, ws["parts"],
                    laptop_row, laptop_data, batches, clear_ranges, collected, errors,
                )

        if not collected:
            raise ValueError("No valid parts found — nothing written")

        new_category = self._calculate_category(laptop_data)
        col = self.cfg["laptop_columns"]
        st = self.cfg["statuses"]
        batches["laptops"].append({
            "range": gspread.utils.rowcol_to_a1(laptop_row, col["warehouse"]),
            "values": [[st["warehouse_value"]]],
        })
        batches["laptops"].append({
            "range": gspread.utils.rowcol_to_a1(laptop_row, col["status"]),
            "values": [[st["assembled_status"]]],
        })
        batches["laptops"].append({
            "range": gspread.utils.rowcol_to_a1(laptop_row, col["category"]),
            "values": [[new_category]],
        })

        self._write_batches(ws, batches, clear_ranges)

        collected.sort(key=lambda item: (self.cfg["sort_order"].get(item["type"], 100), item["type"]))
        report_lines = [item["report"] for item in collected]
        tech_lines = [item["tech"] for item in collected]
        if errors:
            report_lines.append("\n[ERRORS]:\n" + "\n".join(errors))

        return serial, report_lines, tech_lines
