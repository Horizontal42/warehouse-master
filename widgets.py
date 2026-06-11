from __future__ import annotations

import os

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class RangeRowWidget(QWidget):
    def __init__(self, on_action, on_change):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.inp_start = QLineEdit()
        self.inp_start.setPlaceholderText("Start")
        self.inp_start.setValidator(QIntValidator(0, 9_999_999))
        self.inp_start.textChanged.connect(on_change)

        self.inp_end = QLineEdit()
        self.inp_end.setPlaceholderText("End")
        self.inp_end.setValidator(QIntValidator(0, 9_999_999))
        self.inp_end.textChanged.connect(on_change)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(30, 30)
        self.btn_add.clicked.connect(lambda: on_action(self, "add"))

        self.btn_del = QPushButton("–")
        self.btn_del.setFixedSize(30, 30)
        self.btn_del.clicked.connect(lambda: on_action(self, "del"))

        layout.addWidget(self.inp_start)
        layout.addWidget(QLabel("➜"))
        layout.addWidget(self.inp_end)
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_del)

    def get_values(self) -> tuple[int, int] | None:
        s, e = self.inp_start.text(), self.inp_end.text()
        if s and e:
            return int(s), int(e)
        return None

    def set_delete_enabled(self, enabled: bool) -> None:
        self.btn_del.setEnabled(enabled)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("WarehouseMaster", "App")
        from strings import STRINGS
        locale = self.settings.value("locale", "en")
        self._t = STRINGS.get(locale, STRINGS["en"])
        self.setWindowTitle(self._t["dlg_title"])
        self.setFixedSize(450, 290)
        self._init_ui()
        self._load()

    def _init_ui(self):
        t = self._t
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cb_language = NoScrollComboBox()
        self.cb_language.addItems(["English", "Русский"])
        form.addRow(t["dlg_language"], self.cb_language)

        self.cb_theme = NoScrollComboBox()
        self.cb_theme.addItems([t["theme_dark"], t["theme_light"]])
        form.addRow(t["dlg_theme"], self.cb_theme)

        self.inp_url = QLineEdit()
        form.addRow(t["dlg_sheet_url"], self.inp_url)

        path_row = QHBoxLayout()
        self.inp_path = QLineEdit()
        self.inp_path.setReadOnly(True)
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(self.inp_path)
        path_row.addWidget(btn_browse)
        form.addRow(t["dlg_save_folder"], path_row)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btn_save = QPushButton(t["btn_save"])
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton(t["btn_cancel"])
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, self._t["dlg_select_folder"], self.inp_path.text()
        )
        if folder:
            self.inp_path.setText(folder)

    def _load(self):
        locale = self.settings.value("locale", "en")
        self.cb_language.setCurrentIndex(0 if locale == "en" else 1)
        self.cb_theme.setCurrentIndex(self.settings.value("theme_idx", 0, type=int))
        self.inp_path.setText(
            self.settings.value("save_path", os.path.join(os.path.expanduser("~"), "Desktop"))
        )
        self.inp_url.setText(self.settings.value("sheet_url", ""))

    def _save(self):
        self.settings.setValue("locale", "en" if self.cb_language.currentIndex() == 0 else "ru")
        self.settings.setValue("theme_idx", self.cb_theme.currentIndex())
        self.settings.setValue("save_path", self.inp_path.text())
        self.settings.setValue("sheet_url", self.inp_url.text())
        self.accept()
