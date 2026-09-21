from __future__ import annotations
from typing import Optional, List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from models.dataset import Dataset
from core.project import Project
from core.comparator import DatasetComparator, DatasetComparisonReport


class ComparisonMetricCard(QFrame):
    def __init__(self, title: str, count: int, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("CardTitle")
        layout.addWidget(t_lbl)

        self.v_lbl = QLabel(str(count))
        self.v_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 800;")
        layout.addWidget(self.v_lbl)

    def set_count(self, count: int):
        self.v_lbl.setText(str(count))


class ComparisonView(QWidget):
    """Cross-document and longitudinal dataset comparison view (e.g. 2024 OIHD vs 2025 OIHD)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QVBoxLayout()
        title = QLabel("Dataset Edition & Longitudinal Comparison")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        header.addWidget(title)

        subtitle = QLabel("Compare extractions across time periods, survey quarters, or report revisions to track new, modified, and removed records.")
        subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Selection Bar
        sel_bar = QHBoxLayout()
        sel_bar.setSpacing(12)

        lbl1 = QLabel("Baseline Dataset:")
        lbl1.setStyleSheet("color: #94A3B8; font-weight: 600;")
        sel_bar.addWidget(lbl1)

        self.combo_base = QComboBox()
        self.combo_base.setMinimumWidth(180)
        sel_bar.addWidget(self.combo_base)

        lbl2 = QLabel("Comparison Dataset:")
        lbl2.setStyleSheet("color: #94A3B8; font-weight: 600;")
        sel_bar.addWidget(lbl2)

        self.combo_target = QComboBox()
        self.combo_target.setMinimumWidth(180)
        sel_bar.addWidget(self.combo_target)

        self.btn_compare = QPushButton("⚡ Compare Datasets")
        self.btn_compare.setObjectName("PrimaryButton")
        self.btn_compare.clicked.connect(self.run_comparison)
        sel_bar.addWidget(self.btn_compare)

        sel_bar.addStretch()
        layout.addLayout(sel_bar)

        # 4 Metric Cards
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(14)

        self.card_added = ComparisonMetricCard("NEW / ADDED RECORDS", 0, color="#22C55E")
        metrics_grid.addWidget(self.card_added, 0, 0)

        self.card_modified = ComparisonMetricCard("MODIFIED RECORDS", 0, color="#F59E0B")
        metrics_grid.addWidget(self.card_modified, 0, 1)

        self.card_removed = ComparisonMetricCard("REMOVED RECORDS", 0, color="#EF4444")
        metrics_grid.addWidget(self.card_removed, 0, 2)

        self.card_unchanged = ComparisonMetricCard("UNCHANGED RECORDS", 0, color="#94A3B8")
        metrics_grid.addWidget(self.card_unchanged, 0, 3)

        layout.addLayout(metrics_grid)

        # Diff Table
        diff_frame = QFrame()
        diff_frame.setObjectName("Card")
        d_layout = QVBoxLayout(diff_frame)
        d_layout.setContentsMargins(14, 12, 14, 12)
        d_layout.setSpacing(8)

        d_title = QLabel("RECORD DIFFERENCE SPECIFICATION")
        d_title.setObjectName("CardTitle")
        d_layout.addWidget(d_title)

        self.diff_table = QTableWidget(0, 4)
        self.diff_table.setHorizontalHeaderLabels(["Record Key", "Change Type", "Changed Fields", "Values (Old ➔ New)"])
        self.diff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.diff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.diff_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.diff_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.diff_table.verticalHeader().setVisible(False)
        d_layout.addWidget(self.diff_table)

        layout.addWidget(diff_frame)

    def refresh(self, project: Project):
        self.current_project = project
        self.combo_base.clear()
        self.combo_target.clear()

        for name in project.datasets.keys():
            self.combo_base.addItem(name)
            self.combo_target.addItem(name)

        if len(project.datasets) >= 2:
            self.combo_target.setCurrentIndex(1)

    def run_comparison(self):
        if not self.current_project:
            return

        name1 = self.combo_base.currentText()
        name2 = self.combo_target.currentText()

        if not name1 or not name2 or name1 not in self.current_project.datasets or name2 not in self.current_project.datasets:
            return

        ds1 = self.current_project.datasets[name1]
        ds2 = self.current_project.datasets[name2]

        report = DatasetComparator.compare(ds1, ds2)

        self.card_added.set_count(report.added_count)
        self.card_modified.set_count(report.modified_count)
        self.card_removed.set_count(report.removed_count)
        self.card_unchanged.set_count(report.unchanged_count)

        all_diffs = report.modified_records + report.added_records + report.removed_records
        self.diff_table.setRowCount(len(all_diffs))

        for row_idx, diff in enumerate(all_diffs):
            self.diff_table.setItem(row_idx, 0, QTableWidgetItem(diff.key))
            self.diff_table.setItem(row_idx, 1, QTableWidgetItem(diff.diff_type))
            self.diff_table.setItem(row_idx, 2, QTableWidgetItem(", ".join(diff.changed_fields) if diff.changed_fields else "-"))

            val_str = ""
            if diff.diff_type == "MODIFIED":
                val_str = "; ".join([f"{f}: '{diff.old_values.get(f)}' ➔ '{diff.new_values.get(f)}'" for f in diff.changed_fields])
            elif diff.diff_type == "ADDED":
                val_str = f"New Record ({len(diff.new_values)} fields)"
            elif diff.diff_type == "REMOVED":
                val_str = f"Deleted Record ({len(diff.old_values)} fields)"

            self.diff_table.setItem(row_idx, 3, QTableWidgetItem(val_str))
