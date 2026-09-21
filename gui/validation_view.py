from __future__ import annotations
from typing import Optional, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from models.validation import ValidationSummary, IssueSeverity, ValidationIssue
from core.project import Project
from core.validator import Validator


class ValidationCard(QFrame):
    def __init__(self, title: str, count: int, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        t_lbl = QLabel(title.upper())
        t_lbl.setObjectName("CardTitle")
        layout.addWidget(t_lbl)

        self.val_lbl = QLabel(str(count))
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 600; letter-spacing: -0.02em;")
        layout.addWidget(self.val_lbl)

    def set_count(self, count: int):
        self.val_lbl.setText(str(count))


class ValidationView(QWidget):
    """Validation issues dashboard showing critical, warning, and informational integrity checks."""

    auto_fix_applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.validator = Validator()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Validation & Quality")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #FFFFFF; letter-spacing: -0.02em;")
        title_box.addWidget(title)

        subtitle = QLabel("Rule-based integrity checks for required fields, numeric bounds, expressions, and relations.")
        subtitle.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.45);")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()

        self.btn_autofix = QPushButton("Auto-fix Issues")
        self.btn_autofix.setObjectName("PrimaryButton")
        self.btn_autofix.clicked.connect(self.run_auto_fixes)
        header.addWidget(self.btn_autofix)

        layout.addLayout(header)

        # 3 Severity Cards
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.card_crit = ValidationCard("Critical Issues", 0, color="#EF4444")
        cards_grid.addWidget(self.card_crit, 0, 0)

        self.card_warn = ValidationCard("Warnings", 0, color="#F59E0B")
        cards_grid.addWidget(self.card_warn, 0, 1)

        self.card_info = ValidationCard("Auto-fixable Detected", 0, color="#10A37F")
        cards_grid.addWidget(self.card_info, 0, 2)

        layout.addLayout(cards_grid)

        # Issues Table
        table_frame = QFrame()
        table_frame.setObjectName("Card")
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(16, 14, 16, 14)
        t_layout.setSpacing(10)

        t_title = QLabel("Detected Issues")
        t_title.setObjectName("CardTitle")
        t_layout.addWidget(t_title)

        self.issues_table = QTableWidget(0, 6)
        self.issues_table.setHorizontalHeaderLabels([
            "Severity", "Field Name", "Rule Name", "Issue Message", "Current Value", "Auto-Fixable"
        ])
        self.issues_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.issues_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.issues_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.issues_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.issues_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.issues_table.verticalHeader().setVisible(False)
        t_layout.addWidget(self.issues_table)

        layout.addWidget(table_frame)

    def refresh(self, project: Project):
        self.current_project = project
        issues: List[ValidationIssue] = []

        if project and project.validation_summary:
            issues = project.validation_summary.issues

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL and not i.is_fixed)
        warn_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING and not i.is_fixed)
        auto_count = sum(1 for i in issues if i.is_auto_fixable and not i.is_fixed)

        self.card_crit.set_count(crit_count)
        self.card_warn.set_count(warn_count)
        self.card_info.set_count(auto_count)

        self.issues_table.blockSignals(True)
        active_issues = [i for i in issues if not i.is_fixed]
        self.issues_table.setRowCount(len(active_issues))

        for row_idx, issue in enumerate(active_issues):
            self.issues_table.setItem(row_idx, 0, QTableWidgetItem(issue.severity.value))
            self.issues_table.setItem(row_idx, 1, QTableWidgetItem(issue.field_name or "-"))
            self.issues_table.setItem(row_idx, 2, QTableWidgetItem(issue.rule_name))
            self.issues_table.setItem(row_idx, 3, QTableWidgetItem(issue.message))
            self.issues_table.setItem(row_idx, 4, QTableWidgetItem(str(issue.current_value)))
            self.issues_table.setItem(row_idx, 5, QTableWidgetItem("Yes" if issue.is_auto_fixable else "Manual Review"))

        self.issues_table.blockSignals(False)

    def run_auto_fixes(self):
        if not self.current_project or not self.current_project.validation_summary:
            return

        fixed_total = 0
        for ds in self.current_project.datasets.values():
            fixed = self.validator.apply_auto_fixes(ds, self.current_project.validation_summary)
            fixed_total += fixed

        self.current_project.save()
        self.refresh(self.current_project)
        self.auto_fix_applied.emit()
        QMessageBox.information(self, "Auto-Fix Applied", f"Successfully resolved {fixed_total} validation issues deterministically.")
