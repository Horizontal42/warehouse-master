from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "single": (58 * mm, 40 * mm),
    "grid_2x2": (58 * mm, 40 * mm),
    "grid_4x4": (120 * mm, 75 * mm),
}
DEFAULT_FONT_SIZES: dict[str, int] = {"single": 32, "grid_2x2": 24, "grid_4x4": 36}


class PDFWorker(QThread):
    finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, ranges, label_type, label_name, font_size, font_name, filepath):
        super().__init__()
        self.ranges = ranges
        self.label_type = label_type
        self.label_name = label_name
        self.font_size = font_size
        self.font_name = font_name
        self.filepath = filepath

    def run(self):
        try:
            if not self.ranges:
                raise ValueError("No ranges defined")
            pw, ph = PAGE_SIZES[self.label_type]
            if self.label_type == "single":
                page_size = landscape((pw, ph))
                cols, rows = 1, 1
            elif self.label_type == "grid_2x2":
                page_size = (pw, ph)
                cols, rows = 2, 2
            else:
                page_size = (pw, ph)
                cols, rows = 4, 4
            c = canvas.Canvas(self.filepath, pagesize=page_size)
            c.setFont(self.font_name, self.font_size)
            cell_w = pw / cols
            cell_h = ph / rows
            items_per_page = cols * rows
            idx = 0
            for start, end in self.ranges:
                for num in range(start, end + 1):
                    col = idx % cols
                    row = idx // cols
                    if self.label_type == "single":
                        c.drawCentredString(pw / 2, ph / 2 + 5 * mm, self.label_name)
                        c.drawCentredString(pw / 2, ph / 2 - 5 * mm, f"№ {num}")
                    else:
                        x = col * cell_w + cell_w / 2
                        y = ph - (row + 1) * cell_h + cell_h / 2 - self.font_size / 3
                        c.drawCentredString(x, y, str(num))
                    idx += 1
                    if idx >= items_per_page:
                        c.showPage()
                        c.setFont(self.font_name, self.font_size)
                        idx = 0
            if idx > 0:
                c.showPage()
            c.save()
            self.finished.emit(self.filepath)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ReassemblyWorker(QThread):
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)

    def __init__(self, sheet_url, cfg_path, order_prefix, order_num, laptop_id, parts_str, ssd_id, akb_id):
        super().__init__()
        self.sheet_url = sheet_url
        self.cfg_path = cfg_path
        self.order_prefix = order_prefix
        self.order_num = order_num
        self.laptop_id = laptop_id
        self.parts_str = parts_str
        self.ssd_id = ssd_id
        self.akb_id = akb_id

    def run(self):
        try:
            try:
                from sheet_manager import SheetManager
            except ImportError as e:
                self.error_signal.emit(f"Google Sheets dependencies not installed: {e}")
                return
            manager = SheetManager(self.sheet_url, self.cfg_path)
            serial, report_lines, tech_lines = manager.process_reassembly(
                self.laptop_id, self.parts_str, self.ssd_id, self.akb_id
            )
            comment = (
                f"{self.order_prefix} {self.order_num}\n"
                f"{self.laptop_id} {serial}\n"
                + "\n".join(report_lines)
            )
            tech_op = f"Parts for {self.laptop_id} (S/N {serial}):\n" + "\n".join(tech_lines)
            self.finished_signal.emit(comment, tech_op)
        except Exception as e:
            self.error_signal.emit(str(e))
