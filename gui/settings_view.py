from __future__ import annotations
import yaml
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QPlainTextEdit,
    QMessageBox,
)


class SettingsView(QWidget):
    """Configuration settings and extraction profile editor view."""

    def __init__(self, config_path: str = "config/config.yaml", parent=None):
        super().__init__(parent)
        self.config_path = Path(config_path).resolve()
        self.profiles_dir = self.config_path.parent / "profiles"
        self.init_ui()
        self.load_profiles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QVBoxLayout()
        title = QLabel("System Settings & Extraction Profiles")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        header.addWidget(title)

        subtitle = QLabel("Configure OCR engine fallback, parallelism, quality thresholds, and document archetype profiles.")
        subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Settings Card
        settings_card = QFrame()
        settings_card.setObjectName("Card")
        s_layout = QVBoxLayout(settings_card)
        s_layout.setContentsMargins(16, 14, 16, 14)
        s_layout.setSpacing(10)

        st_title = QLabel("ENGINE CONFIGURATION")
        st_title.setObjectName("CardTitle")
        s_layout.addWidget(st_title)

        row1 = QHBoxLayout()
        self.chk_ocr = QCheckBox("Enable Tesseract OCR Engine Fallback for Scanned Documents")
        self.chk_ocr.setChecked(True)
        row1.addWidget(self.chk_ocr)

        row1.addSpacing(20)
        row1.addWidget(QLabel("Parallel Workers:"))
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 16)
        self.spin_workers.setValue(4)
        row1.addWidget(self.spin_workers)
        row1.addStretch()
        s_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Custom Tesseract Path (Optional):"))
        self.txt_tesseract = QLineEdit()
        self.txt_tesseract.setPlaceholderText("e.g. C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        row2.addWidget(self.txt_tesseract)
        s_layout.addLayout(row2)

        layout.addWidget(settings_card)

        # Profiles Card
        prof_card = QFrame()
        prof_card.setObjectName("Card")
        p_layout = QVBoxLayout(prof_card)
        p_layout.setContentsMargins(16, 14, 16, 14)
        p_layout.setSpacing(10)

        p_header = QHBoxLayout()
        p_title = QLabel("EXTRACTION PROFILES (YAML)")
        p_title.setObjectName("CardTitle")
        p_header.addWidget(p_title)

        p_header.addStretch()
        p_header.addWidget(QLabel("Select Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_selected)
        p_header.addWidget(self.profile_combo)

        self.btn_save_prof = QPushButton("💾 Save Profile")
        self.btn_save_prof.setObjectName("PrimaryButton")
        self.btn_save_prof.clicked.connect(self.save_current_profile)
        p_header.addWidget(self.btn_save_prof)

        p_layout.addLayout(p_header)

        self.profile_editor = QPlainTextEdit()
        self.profile_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #070B16;
                color: #F8FAFC;
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #263244;
                border-radius: 4px;
            }
        """)
        p_layout.addWidget(self.profile_editor)

        layout.addWidget(prof_card)

    def load_profiles(self):
        self.profile_combo.clear()
        if not self.profiles_dir.exists():
            return

        for p_file in self.profiles_dir.glob("*.yaml"):
            self.profile_combo.addItem(p_file.name, str(p_file))

    def on_profile_selected(self, idx: int):
        file_path = self.profile_combo.currentData()
        if file_path and Path(file_path).exists():
            with open(file_path, "r", encoding="utf-8") as f:
                self.profile_editor.setPlainText(f.read())

    def save_current_profile(self):
        file_path = self.profile_combo.currentData()
        if not file_path:
            return

        try:
            # Validate YAML syntax
            content = self.profile_editor.toPlainText()
            yaml.safe_load(content)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(self, "Profile Saved", f"Successfully updated {Path(file_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "YAML Syntax Error", f"Failed to save profile: {e}")
