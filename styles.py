def build_stylesheet(dark: bool) -> str:
    if dark:
        bg, text = "#212529", "#f8f9fa"
        inp_bg, inp_border = "#343a40", "#6c757d"
        btn_bg, btn_hover = "#343a40", "#495057"
        menu_sel, disabled_btn = "#0D6EFD", "#555555"
        active_inp, disabled_inp = "#ffffff", "#6c757d"
        menu_bg = "#2b2b2b"
    else:
        bg, text = "#f8f9fa", "#212529"
        inp_bg, inp_border = "#ffffff", "#ced4da"
        btn_bg, btn_hover = "#e9ecef", "#dee2e6"
        menu_sel, disabled_btn = "#0D6EFD", "#cccccc"
        active_inp, disabled_inp = "#212529", "#adb5bd"
        menu_bg = "#f0f0f0"

    return f"""
        QMainWindow, QWidget {{ background-color: {bg}; color: {text}; font-family: 'Segoe UI', sans-serif; }}
        QMenuBar {{ background-color: {btn_bg}; color: {text}; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background-color: {menu_sel}; color: white; }}
        QMenu {{ background-color: {menu_bg}; color: {text}; border: 1px solid {inp_border}; }}
        QGroupBox {{ border: 1px solid {inp_border}; border-radius: 6px; margin-top: 12px; padding-top: 10px; font-weight: bold; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
        QLineEdit, QSpinBox, QComboBox, QTextEdit {{ background-color: {inp_bg}; color: {active_inp}; border: 1px solid {inp_border}; padding: 6px; border-radius: 4px; }}
        QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background-color: {bg}; color: {disabled_inp}; border: 1px dashed {inp_border}; }}
        QCheckBox {{ color: {text}; }}
        QPushButton {{ background-color: {btn_bg}; border: 1px solid {inp_border}; border-radius: 4px; color: {text}; font-weight: bold; }}
        QPushButton:hover {{ background-color: {btn_hover}; }}
        QPushButton[text="+"] {{ color: #2ecc71; font-size: 16px; }}
        QPushButton[text="–"] {{ color: #e74c3c; font-size: 16px; }}
        QPushButton[text="–"]:disabled {{ color: {disabled_btn}; border-color: {disabled_btn}; background-color: transparent; }}
        QPushButton#btn_gen {{ background-color: #0d6efd; color: white; border: none; font-size: 14px; }}
        QPushButton#btn_gen:hover {{ background-color: #0b5ed7; }}
        QScrollArea {{ border: none; }}
        QTabWidget::pane {{ border: 1px solid {inp_border}; }}
        QTabBar::tab {{ background: {btn_bg}; color: {text}; padding: 10px; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
        QTabBar::tab:selected {{ background: {menu_sel}; color: white; }}
    """
