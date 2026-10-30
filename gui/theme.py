"""Dark visual theme for the FloodGuard Studio desktop interface."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#0A121C",
    "surface": "#101C2A",
    "surface_alt": "#152438",
    "surface_raised": "#192B42",
    "border": "#243A52",
    "border_soft": "#1B2C40",
    "text": "#E9F1F8",
    "text_muted": "#91A6BB",
    "text_faint": "#6C8298",
    "accent": "#2BC4D9",
    "accent_hover": "#4DD8EA",
    "accent_dark": "#0E7C8C",
    "success": "#36C98F",
    "warning": "#F0B34A",
    "danger": "#F47070",
    "info": "#62A8F5",
    "navy": "#0D3B52",
    "button_text": "#06121A",
}

STATUS_COLORS = {
    "Within calculated capacity": COLORS["success"],
    "Approaching calculated capacity": COLORS["warning"],
    "Calculated demand exceeds capacity": COLORS["danger"],
}


def application_font() -> QFont:
    available = set(QFontDatabase.families())
    for family in ("Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"):
        if family in available:
            font = QFont(family)
            font.setPointSize(10)
            return font
    return QFont()


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(application_font())
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent_dark"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORS["surface_raised"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS["text_faint"]))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)


STYLESHEET = f"""
QWidget {{
    color: {COLORS["text"]};
    background: transparent;
    selection-background-color: {COLORS["accent_dark"]};
    selection-color: #FFFFFF;
}}
QMainWindow, QDialog {{
    background: {COLORS["bg"]};
}}
QWidget#AppRoot {{
    background: {COLORS["bg"]};
}}
QFrame#Sidebar {{
    background: #0C1724;
    border-right: 1px solid {COLORS["border_soft"]};
}}
QFrame#Topbar {{
    background: {COLORS["surface"]};
    border-bottom: 1px solid {COLORS["border_soft"]};
}}
QFrame#PropertiesPanel {{
    background: {COLORS["surface"]};
    border-left: 1px solid {COLORS["border_soft"]};
}}
QFrame#Card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 12px;
}}
QFrame#HeroCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #10283A, stop:0.55 #102236, stop:1 #101C2A);
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
}}
QFrame#ScopeBanner {{
    background: #12283A;
    border: 1px solid #24516A;
    border-left: 3px solid {COLORS["accent"]};
    border-radius: 8px;
}}
QFrame#WarningBanner {{
    background: #2A2317;
    border: 1px solid #5B4724;
    border-left: 3px solid {COLORS["warning"]};
    border-radius: 8px;
}}
QLabel#BrandMark {{
    background: {COLORS["accent"]};
    color: #071018;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 800;
}}
QLabel#BrandName {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#BrandSub {{
    color: {COLORS["text_muted"]};
    font-size: 9px;
}}
QLabel#PageTitle {{
    font-size: 24px;
    font-weight: 700;
    color: {COLORS["text"]};
}}
QLabel#PageSubtitle {{
    font-size: 11px;
    color: {COLORS["text_muted"]};
}}
QLabel#SectionTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {COLORS["text"]};
}}
QLabel#CardTitle {{
    font-size: 10px;
    font-weight: 700;
    color: {COLORS["text_muted"]};
    letter-spacing: 1px;
}}
QLabel#Muted {{
    color: {COLORS["text_muted"]};
    font-size: 10px;
}}
QLabel#Faint {{
    color: {COLORS["text_faint"]};
    font-size: 9px;
}}
QLabel#KpiValue {{
    font-size: 23px;
    font-weight: 700;
    color: {COLORS["text"]};
}}
QLabel#KpiUnit {{
    color: {COLORS["text_muted"]};
    font-size: 10px;
}}
QLabel#Formula {{
    font-family: "DejaVu Sans Mono", "Consolas", monospace;
    font-size: 11px;
    color: {COLORS["accent"]};
    background: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 7px;
    padding: 8px 10px;
}}
QLabel#StatusPill {{
    background: {COLORS["surface_raised"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 600;
}}
QLabel#WarningText {{
    color: {COLORS["warning"]};
    font-size: 10px;
}}
QLabel#DangerText {{
    color: {COLORS["danger"]};
    font-size: 10px;
}}
QLabel#SuccessText {{
    color: {COLORS["success"]};
    font-size: 10px;
}}
QPushButton {{
    background: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 10px;
    font-weight: 600;
    color: {COLORS["text"]};
}}
QPushButton:hover {{
    background: {COLORS["surface_raised"]};
    border-color: {COLORS["accent_dark"]};
}}
QPushButton:pressed {{
    background: {COLORS["accent_dark"]};
}}
QPushButton:disabled {{
    color: {COLORS["text_faint"]};
    background: {COLORS["surface"]};
    border-color: {COLORS["border_soft"]};
}}
QPushButton#PrimaryButton {{
    background: {COLORS["accent"]};
    border: 1px solid {COLORS["accent"]};
    color: #06121A;
    font-weight: 700;
}}
QPushButton#PrimaryButton:hover {{
    background: {COLORS["accent_hover"]};
    border-color: {COLORS["accent_hover"]};
}}
QPushButton#DangerButton {{
    color: {COLORS["danger"]};
    border-color: #5A2C32;
}}
QPushButton#DangerButton:hover {{
    background: #3A2026;
}}
QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid {COLORS["border_soft"]};
}}
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px;
}}
QToolButton:hover {{
    background: {COLORS["surface_alt"]};
    border-color: {COLORS["border"]};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 8px;
    color: {COLORS["text"]};
    font-size: 10px;
    min-height: 18px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {COLORS["accent_dark"]};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {COLORS["text_faint"]};
    background: {COLORS["surface"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {COLORS["surface_raised"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent_dark"]};
    outline: none;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {COLORS["surface_raised"]};
    border: none;
    width: 16px;
}}
QCheckBox {{
    spacing: 8px;
    color: {COLORS["text"]};
    font-size: 10px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    background: {COLORS["surface_alt"]};
}}
QCheckBox::indicator:checked {{
    background: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
}}
QListWidget#Nav {{
    background: transparent;
    border: none;
    outline: none;
    padding: 6px;
}}
QListWidget#Nav::item {{
    background: transparent;
    border-radius: 8px;
    padding: 11px 12px;
    margin: 2px 4px;
    color: {COLORS["text_muted"]};
    font-size: 10px;
    font-weight: 600;
}}
QListWidget#Nav::item:hover {{
    background: {COLORS["surface_alt"]};
    color: {COLORS["text"]};
}}
QListWidget#Nav::item:selected {{
    background: #12384A;
    color: {COLORS["accent"]};
    border-left: 2px solid {COLORS["accent"]};
}}
QTableWidget {{
    background: {COLORS["surface"]};
    alternate-background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 8px;
    gridline-color: {COLORS["border_soft"]};
    font-size: 9px;
    outline: none;
}}
QTableWidget::item {{
    padding: 5px;
}}
QTableWidget::item:selected {{
    background: #174359;
    color: #FFFFFF;
}}
QHeaderView::section {{
    background: {COLORS["surface_alt"]};
    color: {COLORS["text_muted"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    padding: 7px 5px;
    font-size: 9px;
    font-weight: 700;
}}
QTabWidget::pane {{
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 8px;
    background: {COLORS["surface"]};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLORS["text_muted"]};
    padding: 7px 14px;
    border-bottom: 2px solid transparent;
    font-size: 9px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {COLORS["accent"]};
    border-bottom-color: {COLORS["accent"]};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["text_faint"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    border: none;
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-width: 30px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {COLORS["border"]};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {COLORS["accent"]};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QGraphicsView {{
    background: #09121D;
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 8px;
}}
QSplitter::handle {{
    background: {COLORS["border_soft"]};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QStatusBar {{
    background: {COLORS["surface"]};
    color: {COLORS["text_muted"]};
    border-top: 1px solid {COLORS["border_soft"]};
    font-size: 9px;
}}
QStatusBar::item {{
    border: none;
}}
QToolTip {{
    background: {COLORS["surface_raised"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    padding: 5px;
}}
QMenu {{
    background: {COLORS["surface_raised"]};
    border: 1px solid {COLORS["border"]};
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 24px 7px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {COLORS["accent_dark"]};
}}
QMenuBar {{
    background: {COLORS["surface"]};
    color: {COLORS["text"]};
}}
QListWidget {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border_soft"]};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px;
}}
QListWidget::item:selected {{
    background: #174359;
}}
QProgressBar {{
    background: {COLORS["surface_alt"]};
    border: none;
    border-radius: 3px;
    height: 6px;
}}
QProgressBar::chunk {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}
"""
