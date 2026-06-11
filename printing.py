from __future__ import annotations

import os
import platform
import subprocess
import sys

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HAS_WIN32 = False
try:
    if platform.system() == "Windows":
        import win32print
        import win32api
        HAS_WIN32 = True
except ImportError:
    pass


def resource_path(relative_path: str) -> str:
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


def app_data_dir() -> str:
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    path = os.path.join(base, "WarehouseMaster")
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    local = resource_path("sheet_config.json")
    if os.path.exists(local):
        return local
    return os.path.join(app_data_dir(), "sheet_config.json")


def register_fonts() -> str:
    font_path = resource_path("Inter.ttf")
    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("Inter", font_path))
            return "Inter"
    except Exception:
        pass
    return "Helvetica"


def get_installed_printers() -> list[str]:
    if not HAS_WIN32:
        return []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(flags)]
    except OSError:
        return []


def open_file(filepath: str) -> None:
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin":
            subprocess.call(["open", filepath])
        else:
            subprocess.call(["xdg-open", filepath])
    except OSError:
        pass


def print_file(filepath: str, printer_name: str | None = None) -> None:
    try:
        if platform.system() == "Windows":
            if printer_name and HAS_WIN32:
                win32api.ShellExecute(0, "printto", filepath, f'"{printer_name}"', ".", 0)
            else:
                os.startfile(filepath, "print")
        else:
            subprocess.call(["lp", filepath])
    except OSError:
        open_file(filepath)
