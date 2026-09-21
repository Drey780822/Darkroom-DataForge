"""Darkroom DataForge - Minimalist Notion AI / OpenAI Inspired Dark Theme.

Palette:
  Canvas Background:       #0A0A0C
  Sidebar Background:      #0F0F12
  Card Surface:            #141418
  Secondary Surface:       #19191E
  Subtle Borders:          rgba(255, 255, 255, 0.07)
  Focus / Hover Borders:   rgba(255, 255, 255, 0.20)
  Primary Text:            #EDEDED
  Secondary Text:          #8E8E93
  Muted / Meta Text:       #5C5C62
  Accent Mint (OpenAI):    #10A37F
  Accent Amber (Warning):  #F5A623
  Accent Coral (Danger):   #E5534B
"""

DARKROOM_STYLE = """
/* Global Window & Typography */
QWidget {
    background-color: #0A0A0C;
    color: #EDEDED;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    outline: none;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #0F0F12;
    border-right: 1px solid rgba(255, 255, 255, 0.07);
}

QLabel#BrandTitle {
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
}

QLabel#BrandSubtitle {
    color: #8E8E93;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #8E8E93;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#NavButton:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #EDEDED;
}

QPushButton#NavButton:checked {
    background-color: rgba(255, 255, 255, 0.09);
    color: #FFFFFF;
    font-weight: 600;
}

/* Cards & Surfaces */
QFrame#Card {
    background-color: #141418;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
}

QFrame#SecondaryCard {
    background-color: #19191E;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
}

QLabel#CardTitle {
    color: #8E8E93;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

QLabel#CardValue {
    color: #EDEDED;
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.5px;
}

/* Buttons - Minimalist Monochrome & Mint */
QPushButton {
    background-color: #19191E;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #222228;
    border-color: rgba(255, 255, 255, 0.22);
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #141418;
}

/* Primary Action: Crisp Minimalist Contrast */
QPushButton#PrimaryButton {
    background-color: #EDEDED;
    color: #0A0A0C;
    border: 1px solid #FFFFFF;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #FFFFFF;
    border-color: #FFFFFF;
}

QPushButton#PrimaryButton:pressed {
    background-color: #D6D6D6;
}

/* Secondary Action: Subtle Surface */
QPushButton#NavyButton {
    background-color: #1E1E24;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.12);
    font-weight: 500;
}

QPushButton#NavyButton:hover {
    background-color: #27272F;
    border-color: rgba(255, 255, 255, 0.25);
}

/* Success / Run Action: OpenAI Mint Tint */
QPushButton#SuccessButton {
    background-color: #10A37F;
    color: #FFFFFF;
    border: 1px solid #10A37F;
    font-weight: 600;
}

QPushButton#SuccessButton:hover {
    background-color: #12B98F;
    border-color: #12B98F;
}

QPushButton#SuccessButton:pressed {
    background-color: #0E8E6E;
}

/* Danger Button: Subtle Crimson */
QPushButton#DangerButton {
    background-color: rgba(229, 83, 75, 0.12);
    color: #E5534B;
    border: 1px solid rgba(229, 83, 75, 0.25);
    font-weight: 500;
}

QPushButton#DangerButton:hover {
    background-color: rgba(229, 83, 75, 0.20);
    border-color: rgba(229, 83, 75, 0.45);
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background-color: #121215;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: rgba(255, 255, 255, 0.15);
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {
    border: 1px solid rgba(255, 255, 255, 0.30);
}

QComboBox {
    background-color: #141418;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 6px;
    padding: 5px 12px;
}

QComboBox:focus {
    border-color: rgba(255, 255, 255, 0.30);
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #141418;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.12);
    selection-background-color: rgba(255, 255, 255, 0.08);
}

/* Tables & Grids */
QTableWidget, QTableView, QTreeWidget, QTreeView {
    background-color: #121215;
    color: #EDEDED;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    gridline-color: rgba(255, 255, 255, 0.04);
    selection-background-color: rgba(255, 255, 255, 0.08);
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #16161B;
    color: #8E8E93;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    border: none;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

/* Minimalist Transparent Scrollbars (Notion / OpenAI feel) */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.14);
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.28);
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 6px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.14);
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.28);
}

QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    border: none;
    background: none;
}

/* Status Bar */
QStatusBar {
    background-color: #0F0F12;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    color: #8E8E93;
    font-size: 11px;
    padding: 2px 12px;
}

/* Badges / Status Chips */
QLabel#BadgeSuccess {
    background-color: rgba(16, 163, 127, 0.12);
    color: #10A37F;
    border: 1px solid rgba(16, 163, 127, 0.25);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeWarning {
    background-color: rgba(245, 166, 35, 0.12);
    color: #F5A623;
    border: 1px solid rgba(245, 166, 35, 0.25);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#BadgeCritical {
    background-color: rgba(229, 83, 75, 0.12);
    color: #E5534B;
    border: 1px solid rgba(229, 83, 75, 0.25);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
"""
