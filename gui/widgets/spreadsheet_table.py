from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QAction
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QAbstractItemView,
)
from models.dataset import Dataset
from models.record import Record


class SpreadsheetTable(QTableWidget):
    """High-performance spreadsheet table preview with provenance jump and search filtering."""

    view_source_requested = Signal(str, int)  # (document_filename, page_number)
    record_edited = Signal(str, str, str)     # (record_id, field_name, new_val)
    record_deleted = Signal(str)              # (record_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dataset: Optional[Dataset] = None
        self.filtered_records: List[Record] = []
        self.init_ui()

    def get_selected_record(self) -> Optional[Record]:
        row = self.currentRow()
        if 0 <= row < len(self.filtered_records):
            return self.filtered_records[row]
        return None

    def init_ui(self):
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setDefaultSectionSize(26)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.cellChanged.connect(self.on_cell_changed)

    def load_dataset(self, dataset: Dataset, filter_text: str = ""):
        self.blockSignals(True)
        self.current_dataset = dataset
        self.clear()

        # Headers
        col_names = dataset.column_names
        self.setColumnCount(len(col_names))
        self.setHorizontalHeaderLabels([col.replace("_", " ").title() for col in col_names])

        # Filter records
        f_lower = filter_text.strip().lower()
        if not f_lower:
            self.filtered_records = list(dataset.records)
        else:
            self.filtered_records = [
                r for r in dataset.records
                if any(f_lower in str(v).lower() for v in r.to_dict().values() if v is not None)
            ]

        self.setRowCount(len(self.filtered_records))

        # Populate rows
        for row_idx, record in enumerate(self.filtered_records):
            for col_idx, col_name in enumerate(col_names):
                cell = record.cells.get(col_name)
                val = record.get_value(col_name, prefer_normalized=True)
                val_str = "" if val is None else str(val)

                item = QTableWidgetItem(val_str)

                # Visual cues for normalization modification or validation flags
                if cell and cell.is_modified:
                    # Subtle highlight for normalized values
                    item.setForeground(QBrush(QColor("#93C5FD")))  # soft blue
                if record.is_flagged_for_review:
                    item.setBackground(QBrush(QColor(239, 68, 68, 25)))  # faint red

                self.setItem(row_idx, col_idx, item)

        self.blockSignals(False)

    def on_cell_changed(self, row: int, col: int):
        if not self.current_dataset or row >= len(self.filtered_records):
            return

        rec = self.filtered_records[row]
        field_name = self.current_dataset.column_names[col]
        new_val = self.item(row, col).text()

        # Update record
        raw_val = rec.cells[field_name].raw_value if field_name in rec.cells else new_val
        rec.set_value(field_name, raw_val, new_val)
        self.record_edited.emit(rec.id, field_name, new_val)

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        row = item.row()
        if row >= len(self.filtered_records):
            return

        rec = self.filtered_records[row]
        menu = QMenu(self)

        action_source = QAction(f"Jump to Source (Page {rec.provenance.source_page})", self)
        action_source.triggered.connect(lambda: self.view_source_requested.emit(
            rec.provenance.source_document,
            rec.provenance.source_page
        ))
        menu.addAction(action_source)

        action_raw = QAction("View Raw Value", self)
        col = item.column()
        field_name = self.current_dataset.column_names[col]
        raw_val = rec.cells[field_name].raw_value if field_name in rec.cells else ""
        action_raw.triggered.connect(lambda: item.setToolTip(f"Raw source value: {raw_val}"))
        menu.addAction(action_raw)

        menu.exec(self.mapToGlobal(pos))

    def on_item_double_clicked(self, item):
        row = item.row()
        if row < len(self.filtered_records):
            rec = self.filtered_records[row]
            self.view_source_requested.emit(
                rec.provenance.source_document,
                rec.provenance.source_page
            )
