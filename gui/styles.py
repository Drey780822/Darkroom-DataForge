"""Darkroom DataForge - Professional Darkroom Dark Theme Stylesheet.

Palette:
  Background:        #0B1020
  Surface:           #111827
  Secondary Surface: #172033
  Primary Text:      #F8FAFC
  Secondary Text:    #94A3B8
  Darkroom Navy:     #1D3557
  Darkroom Gold:     #D4AF37
  Borders:           #263244
  Success:           #22C55E
  Warning:           #F59E0B
  Error:             #EF4444
"""

DARKROOM_STYLE = """
/* Global Window & Fonts */
QWidget {
    background-color: #0B1020;
    color: #F8FAFC;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    outline: none;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #111827;
    border-right: 1px solid #263244;
}

QLabel#BrandTitle {
    color: #F8FAFC;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

QLabel#BrandSubtitle {
    color: #D4AF37;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#NavButton:hover {
    background-color: #172033;
    color: #F8FAFC;
}

QPushButton#NavButton:checked {
    background-color: #1D3557;
    color: #F8FAFC;
    border-left: 3px solid #D4AF37;
    font-weight: 600;
}

/* Cards & Surfaces */
QFrame#Card {
    background-color: #111827;
    border: 1px solid #263244;
    border-radius: 8px;
}

QFrame#SecondaryCard {
    background-color: #172033;
    border: 1px solid #263244;
    border-radius: 6px;
}

QLabel#CardTitle {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QLabel#CardValue {
    color: #F8FAFC;
    font-size: 26px;
    font-weight: 700;
}

/* Buttons */
QPushButton {
    background-color: #172033;
    color: #F8FAFC;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1D3557;
    border-color: #D4AF37;
}

QPushButton:pressed {
    background-color: #0F172A;
}

QPushButton#PrimaryButton {
    background-color: #D4AF37;
    color: #0B1020;
    border: 1px solid #B5942B;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover {
    background-color: #E6C35C;
}

QPushButton#NavyButton {
    background-color: #1D3557;
    color: #FFFFFF;
    border: 1px solid #2A4A75;
    font-weight: 600;
}

QPushButton#NavyButton:hover {
    background-color: #24426C;
}

QPushButton#SuccessButton {
    background-color: #22C55E;
    color: #0B1020;
    border: none;
    font-weight: 600;
}

QPushButton#DangerButton {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
    font-weight: 600;
}

/* Input Fields & Combos */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #1D3557;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {
    border: 1px solid #D4AF37;
}

QComboBox {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #263244;
    border-radius: 6px;
    padding: 6px 12px;
}

QComboBox:focus {
    border-color: #D4AF37;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #263244;
}

QComboBox QAbstractItemView {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #263244;
    selection-background-color: #1D3557;
}

/* Tables & Tree Views */
QTableWidget, QTableView, QTreeWidget, QTreeView {
    background-color: #111827;
    color: #F8FAFC;
    border: 1px solid #263244;
    border-radius: 6px;
    gridline-color: #1E293B;
    selection-background-color: #1D3557;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #172033;
    color: #94A3B8;
    padding: 8px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-right: 1px solid #263244;
    border-bottom: 1px solid #263244;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #0B1020;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #263244;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #D4AF37;
}

QScrollBar:horizontal {
    border: none;
    background: #0B1020;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #263244;
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #D4AF37;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}

/* Status Bar */
QStatusBar {
    background-color: #111827;
    border-top: 1px solid #263244;
    color: #94A3B8;
    font-size: 11px;
}

/* Badges / Chips */
QLabel#BadgeSuccess {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22C55E;
    border: 1px solid #22C55E;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeWarning {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid #F59E0B;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeCritical {
    background-color: rgba(239, 68, 68, 0.15);
    color: #EF4444;
    border: 1px solid #EF4444;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
"""
