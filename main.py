import ctypes
import os
import sys
import tempfile

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction, QApplication, QCheckBox, QDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QSpinBox, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from printing import (
    app_data_dir, config_path, get_installed_printers,
    open_file, print_file, register_fonts, resource_path,
)
from strings import STRINGS
from styles import build_stylesheet
from widgets import NoScrollComboBox, PreferencesDialog, RangeRowWidget
from workers import DEFAULT_FONT_SIZES, PDFWorker, ReassemblyWorker


class LabelApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.font_name = register_fonts()
        self.rows: list[RangeRowWidget] = []
        self.temp_files: list[str] = []
        self.current_type = "single"
        self.settings = QSettings("WarehouseMaster", "App")
        self.locale = self.settings.value("locale", "en")
        self._worker = None
        self._r_worker = None

        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            if sys.platform == "win32":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("warehousemaster.app")

        self._create_menu_bar()
        self._init_ui()
        self._load_state()

    def _s(self, key: str) -> str:
        return STRINGS.get(self.locale, STRINGS["en"]).get(key, key)

    def _create_menu_bar(self):
        self.settings_menu = self.menuBar().addMenu("")
        self.pref_action = QAction("", self)
        self.pref_action.triggered.connect(self._open_preferences)
        self.settings_menu.addAction(self.pref_action)

    def _init_ui(self):
        self.setGeometry(100, 100, 500, 700)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_gen = QWidget()
        self._init_gen_tab()
        self.tabs.addTab(self.tab_gen, "")
        self.tab_reassembly = QWidget()
        self._init_reassembly_tab()
        self.tabs.addTab(self.tab_reassembly, "")

    def _init_gen_tab(self):
        layout = QVBoxLayout(self.tab_gen)
        layout.setSpacing(15)

        self.gb_type = QGroupBox()
        vbox = QVBoxLayout(self.gb_type)
        self.rb_single = QRadioButton()
        self.rb_2x2 = QRadioButton()
        self.rb_4x4 = QRadioButton()
        vbox.addWidget(self.rb_single)
        vbox.addWidget(self.rb_2x2)
        vbox.addWidget(self.rb_4x4)
        layout.addWidget(self.gb_type)

        self.gb_cfg = QGroupBox()
        vbox_cfg = QVBoxLayout(self.gb_cfg)
        row_font = QHBoxLayout()
        self.lbl_font_size = QLabel()
        row_font.addWidget(self.lbl_font_size)
        self.spin_font = QSpinBox()
        self.spin_font.setRange(6, 140)
        row_font.addWidget(self.spin_font)
        vbox_cfg.addLayout(row_font)
        self.inp_name = QLineEdit()
        vbox_cfg.addWidget(self.inp_name)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #555;")
        vbox_cfg.addWidget(line)
        self.chk_autoprint = QCheckBox()
        self.chk_autoprint.toggled.connect(self._toggle_printer)
        vbox_cfg.addWidget(self.chk_autoprint)
        printer_row = QHBoxLayout()
        printer_row.setContentsMargins(10, 0, 0, 0)
        self.lbl_printer = QLabel()
        self.cb_printers = NoScrollComboBox()
        self.cb_printers.addItems(get_installed_printers())
        printer_row.addWidget(self.lbl_printer)
        printer_row.addWidget(self.cb_printers)
        self.printer_widget = QWidget()
        self.printer_widget.setLayout(printer_row)
        vbox_cfg.addWidget(self.printer_widget)
        self.chk_temp = QCheckBox()
        vbox_cfg.addWidget(self.chk_temp)
        layout.addWidget(self.gb_cfg)

        self.gb_ranges = QGroupBox()
        self.ranges_layout = QVBoxLayout()
        ranges_container = QWidget()
        ranges_container.setLayout(self.ranges_layout)
        self.ranges_layout.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(ranges_container)
        gb_ranges_layout = QVBoxLayout(self.gb_ranges)
        gb_ranges_layout.addWidget(scroll)
        layout.addWidget(self.gb_ranges)

        footer = QVBoxLayout()
        self.lbl_total = QLabel()
        self.lbl_total.setAlignment(Qt.AlignRight)
        footer.addWidget(self.lbl_total)
        self.btn_gen = QPushButton()
        self.btn_gen.setObjectName("btn_gen")
        self.btn_gen.setFixedHeight(50)
        self.btn_gen.clicked.connect(self._start_generation)
        footer.addWidget(self.btn_gen)
        layout.addLayout(footer)

        self.rb_single.toggled.connect(self._update_type)
        self.rb_2x2.toggled.connect(self._update_type)
        self.rb_4x4.toggled.connect(self._update_type)
        self._add_range_row()

    def _init_reassembly_tab(self):
        layout = QVBoxLayout(self.tab_reassembly)

        self.grp_info = QGroupBox()
        l_info = QGridLayout(self.grp_info)
        self.cb_order_type = NoScrollComboBox()
        self.inp_order_num = QLineEdit()
        self.inp_laptop_id = QLineEdit()
        self.lbl_r_order = QLabel()
        self.lbl_r_laptop = QLabel()
        l_info.addWidget(self.lbl_r_order, 0, 0)
        order_row = QHBoxLayout()
        order_row.addWidget(self.cb_order_type)
        order_row.addWidget(self.inp_order_num)
        l_info.addLayout(order_row, 0, 1)
        l_info.addWidget(self.lbl_r_laptop, 1, 0)
        l_info.addWidget(self.inp_laptop_id, 1, 1)
        layout.addWidget(self.grp_info)

        self.grp_parts_box = QGroupBox()
        form = QFormLayout(self.grp_parts_box)
        self.inp_parts = QLineEdit()
        self.inp_ssd = QLineEdit()
        self.inp_akb = QLineEdit()
        self.lbl_r_parts = QLabel()
        self.lbl_r_ssd = QLabel()
        self.lbl_r_akb = QLabel()
        form.addRow(self.lbl_r_parts, self.inp_parts)
        form.addRow(self.lbl_r_ssd, self.inp_ssd)
        form.addRow(self.lbl_r_akb, self.inp_akb)
        layout.addWidget(self.grp_parts_box)

        self.btn_execute = QPushButton()
        self.btn_execute.setFixedHeight(45)
        self.btn_execute.setObjectName("btn_gen")
        self.btn_execute.clicked.connect(self._run_reassembly)
        layout.addWidget(self.btn_execute)

        self.grp_res = QGroupBox()
        l_res = QVBoxLayout(self.grp_res)
        self.lbl_r_comment = QLabel()
        self.txt_comment = QTextEdit()
        self.txt_comment.setMaximumHeight(80)
        self.lbl_r_tech = QLabel()
        self.txt_tech = QTextEdit()
        self.txt_tech.setMaximumHeight(80)
        l_res.addWidget(self.lbl_r_comment)
        l_res.addWidget(self.txt_comment)
        l_res.addWidget(self.lbl_r_tech)
        l_res.addWidget(self.txt_tech)
        layout.addWidget(self.grp_res)

    # --- i18n ---

    def _retranslate(self):
        s = self._s
        self.setWindowTitle(s("window_title"))
        self.tabs.setTabText(0, s("tab_labels"))
        self.tabs.setTabText(1, s("tab_reassembly"))
        self.settings_menu.setTitle(s("menu_settings"))
        self.pref_action.setText(s("menu_preferences"))
        # labels tab
        self.gb_type.setTitle(s("grp_label_type"))
        self.gb_cfg.setTitle(s("grp_label_settings"))
        self.gb_ranges.setTitle(s("grp_ranges"))
        self.rb_single.setText(s("rb_single"))
        self.rb_2x2.setText(s("rb_2x2"))
        self.rb_4x4.setText(s("rb_4x4"))
        self.lbl_font_size.setText(s("lbl_font_size"))
        self.inp_name.setPlaceholderText(s("ph_label_name"))
        self.chk_autoprint.setText(s("chk_autoprint"))
        self.lbl_printer.setText(s("lbl_printer"))
        self.chk_temp.setText(s("chk_temp"))
        self._toggle_printer()
        self._recalc_total()
        # reassembly tab
        self.grp_info.setTitle(s("grp_order_info"))
        self.grp_parts_box.setTitle(s("grp_parts"))
        self.grp_res.setTitle(s("grp_result"))
        self.lbl_r_order.setText(s("lbl_order"))
        self.lbl_r_laptop.setText(s("lbl_laptop_id"))
        cur = self.cb_order_type.currentIndex()
        self.cb_order_type.clear()
        self.cb_order_type.addItems(STRINGS.get(self.locale, STRINGS["en"])["order_types"])
        self.cb_order_type.setCurrentIndex(max(cur, 0))
        self.inp_order_num.setPlaceholderText(s("ph_order_num"))
        self.inp_laptop_id.setPlaceholderText(s("ph_laptop_id"))
        self.lbl_r_parts.setText(s("lbl_parts_field"))
        self.inp_parts.setPlaceholderText(s("ph_parts"))
        self.lbl_r_ssd.setText(s("lbl_ssd_field"))
        self.inp_ssd.setPlaceholderText(s("ph_ssd"))
        self.lbl_r_akb.setText(s("lbl_akb_field"))
        self.inp_akb.setPlaceholderText(s("ph_akb"))
        self.btn_execute.setText(s("btn_apply"))
        self.lbl_r_comment.setText(s("lbl_comment"))
        self.lbl_r_tech.setText(s("lbl_tech"))

    # --- Labels tab logic ---

    def _toggle_printer(self):
        is_auto = self.chk_autoprint.isChecked()
        self.printer_widget.setEnabled(is_auto)
        self.btn_gen.setText(self._s("btn_print") if is_auto else self._s("btn_generate"))

    def _handle_range_action(self, widget: RangeRowWidget, action: str):
        if action == "add":
            self._add_range_row(self.ranges_layout.indexOf(widget) + 1)
        elif action == "del" and len(self.rows) > 1:
            widget.deleteLater()
            self.rows.remove(widget)
            for r in self.rows:
                r.set_delete_enabled(len(self.rows) > 1)
            self._recalc_total()

    def _add_range_row(self, index: int = -1):
        row = RangeRowWidget(self._handle_range_action, self._recalc_total)
        if index == -1:
            self.ranges_layout.addWidget(row)
            self.rows.append(row)
        else:
            self.ranges_layout.insertWidget(index, row)
            self.rows.insert(index, row)
        for r in self.rows:
            r.set_delete_enabled(len(self.rows) > 1)
        self._apply_theme()

    def _recalc_total(self):
        total = sum(
            v[1] - v[0] + 1
            for r in self.rows
            for v in [r.get_values()]
            if v and v[0] <= v[1]
        )
        self.lbl_total.setText(self._s("lbl_total").format(n=total))

    def _update_type(self):
        if self.rb_single.isChecked():
            self.current_type = "single"
            self.inp_name.setEnabled(True)
        elif self.rb_2x2.isChecked():
            self.current_type = "grid_2x2"
            self.inp_name.setEnabled(False)
        else:
            self.current_type = "grid_4x4"
            self.inp_name.setEnabled(False)
        self.spin_font.setValue(DEFAULT_FONT_SIZES[self.current_type])

    def _start_generation(self):
        raw = [r.get_values() for r in self.rows]
        ranges = [v for v in raw if v is not None]
        if not ranges:
            QMessageBox.warning(self, self._s("err_title"), self._s("err_no_ranges"))
            return
        invalid = [v for v in ranges if v[0] > v[1]]
        if invalid:
            msg = self._s("err_start_gt_end").format(a=invalid[0][0], b=invalid[0][1])
            QMessageBox.warning(self, self._s("err_title"), msg)
            return
        self._save_state()
        first, last = ranges[0][0], ranges[-1][1]
        safe_name = "".join(c for c in (self.inp_name.text() or "") if c.isalnum()).strip()
        filename = f"labels_{first}-{last}_{safe_name}.pdf" if safe_name else f"labels_{first}-{last}.pdf"
        if self.chk_temp.isChecked():
            folder = tempfile.gettempdir()
        else:
            folder = self.settings.value("save_path", os.path.join(os.path.expanduser("~"), "Desktop"))
            if not os.path.exists(folder):
                folder = tempfile.gettempdir()
        filepath = os.path.join(folder, filename)
        if self.chk_temp.isChecked():
            self.temp_files.append(filepath)
        self.btn_gen.setEnabled(False)
        self.btn_gen.setText(self._s("btn_generating"))
        self._worker = PDFWorker(
            ranges, self.current_type, self.inp_name.text(),
            self.spin_font.value(), self.font_name, filepath,
        )
        self._worker.finished.connect(self._on_pdf_done)
        self._worker.error_occurred.connect(self._on_pdf_error)
        self._worker.start()

    def _on_pdf_done(self, filepath: str):
        self.btn_gen.setEnabled(True)
        self._toggle_printer()
        if self.chk_autoprint.isChecked():
            print_file(filepath, self.cb_printers.currentText())
        else:
            open_file(filepath)

    def _on_pdf_error(self, err: str):
        self.btn_gen.setEnabled(True)
        self._toggle_printer()
        QMessageBox.critical(self, self._s("err_title"), err)

    # --- Reassembly tab logic ---

    def _run_reassembly(self):
        url = self.settings.value("sheet_url", "")
        if not url:
            QMessageBox.warning(self, self._s("err_title"), self._s("err_no_sheet_url"))
            return
        order_num = self.inp_order_num.text()
        lap_id = self.inp_laptop_id.text()
        if not order_num or not lap_id:
            QMessageBox.warning(self, self._s("err_title"), self._s("err_no_order"))
            return
        parts_str = self.inp_parts.text()
        ssd_id = self.inp_ssd.text()
        akb_id = self.inp_akb.text()
        if not parts_str and not ssd_id and not akb_id:
            QMessageBox.warning(self, self._s("err_title"), self._s("err_no_parts"))
            return
        self.btn_execute.setEnabled(False)
        self.btn_execute.setText(self._s("btn_applying"))
        self._r_worker = ReassemblyWorker(
            url, config_path(),
            self.cb_order_type.currentText(), order_num,
            lap_id, parts_str, ssd_id, akb_id,
        )
        self._r_worker.finished_signal.connect(self._on_reassembly_done)
        self._r_worker.error_signal.connect(self._on_reassembly_error)
        self._r_worker.start()

    def _on_reassembly_done(self, comment: str, tech_op: str):
        self.btn_execute.setEnabled(True)
        self.btn_execute.setText(self._s("btn_apply"))
        self.txt_comment.setText(comment)
        self.txt_tech.setText(tech_op)
        QMessageBox.information(self, self._s("msg_done_title"), self._s("msg_done"))
        self._save_state()
        self.inp_parts.clear()
        self.inp_ssd.clear()
        self.inp_akb.clear()
        self.inp_laptop_id.setFocus()

    def _on_reassembly_error(self, err: str):
        self.btn_execute.setEnabled(True)
        self.btn_execute.setText(self._s("btn_apply"))
        QMessageBox.critical(self, self._s("err_title"), err)

    # --- State persistence ---

    def _load_state(self):
        self.locale = self.settings.value("locale", "en")
        t = self.settings.value("type", "single")
        if t == "grid_2x2":
            self.rb_2x2.setChecked(True)
        elif t == "grid_4x4":
            self.rb_4x4.setChecked(True)
        else:
            self.rb_single.setChecked(True)
        self.inp_name.setText(self.settings.value("name", ""))
        self.chk_temp.setChecked(self.settings.value("temp_mode", False, type=bool))
        self.chk_autoprint.setChecked(self.settings.value("auto_print", False, type=bool))
        printer = self.settings.value("selected_printer", "")
        if printer:
            idx = self.cb_printers.findText(printer)
            if idx >= 0:
                self.cb_printers.setCurrentIndex(idx)
        self._update_type()
        self._apply_theme()
        self._retranslate()

    def _save_state(self):
        if self.rb_2x2.isChecked():
            t = "grid_2x2"
        elif self.rb_4x4.isChecked():
            t = "grid_4x4"
        else:
            t = "single"
        self.settings.setValue("type", t)
        self.settings.setValue("name", self.inp_name.text())
        self.settings.setValue("temp_mode", self.chk_temp.isChecked())
        self.settings.setValue("auto_print", self.chk_autoprint.isChecked())
        self.settings.setValue("selected_printer", self.cb_printers.currentText())

    def _open_preferences(self):
        dlg = PreferencesDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.locale = self.settings.value("locale", "en")
            self._apply_theme()
            self._retranslate()

    def _apply_theme(self):
        dark = self.settings.value("theme_idx", 0, type=int) == 0
        self.setStyleSheet(build_stylesheet(dark))

    def closeEvent(self, event):
        for f in self.temp_files:
            try:
                os.remove(f)
            except OSError:
                pass
        self._save_state()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LabelApp()
    window.show()
    sys.exit(app.exec_())
