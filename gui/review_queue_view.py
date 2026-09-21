from __future__ import annotations
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QInputDialog,
    QMessageBox,
)
from models.record import Record
from models.dataset import Dataset
from models.provenance import RecordStatus
from core.project import Project
from .widgets.pdf_canvas import PdfCanvas


class ReviewQueueView(QWidget):
    """Human-in-the-loop review queue with provenance jump and verification controls."""

    record_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.flagged_records: List[Tuple[str, Record, str]] = []  # (dataset_name, record, reason)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Review Queue")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #FFFFFF; letter-spacing: -0.02em;")
        title_box.addWidget(title)

        subtitle = QLabel("Cross-verify low-confidence extractions, schema anomalies, and validation warnings against source pages.")
        subtitle.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.45);")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()
        layout.addLayout(header)

        # Splitter: Left queue table + actions, Right PDF canvas
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Action bar
        action_bar = QHBoxLayout()
        self.count_lbl = QLabel("0 pending")
        self.count_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: rgba(255, 255, 255, 0.5); padding: 4px 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px;")
        action_bar.addWidget(self.count_lbl)

        action_bar.addStretch()

        self.btn_accept = QPushButton("Accept Record")
        self.btn_accept.setObjectName("SuccessButton")
        self.btn_accept.clicked.connect(self.accept_selected)
        action_bar.addWidget(self.btn_accept)

        self.btn_edit = QPushButton("Edit Value")
        self.btn_edit.clicked.connect(self.edit_selected)
        action_bar.addWidget(self.btn_edit)

        self.btn_reject = QPushButton("Reject Record")
        self.btn_reject.setObjectName("DangerButton")
        self.btn_reject.clicked.connect(self.reject_selected)
        action_bar.addWidget(self.btn_reject)

        left_layout.addLayout(action_bar)

        # Queue Table
        self.queue_table = QTableWidget(0, 5)
        self.queue_table.setHorizontalHeaderLabels(["Dataset", "Document", "Page", "Confidence", "Status / Flag"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.itemSelectionChanged.connect(self.on_queue_item_selected)
        left_layout.addWidget(self.queue_table)

        # Record values preview
        self.detail_frame = QFrame()
        self.detail_frame.setObjectName("Card")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(14, 12, 14, 12)
        self.detail_lbl = QLabel("Select a record to inspect cell values.")
        self.detail_lbl.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6); line-height: 1.4;")
        self.detail_lbl.setWordWrap(True)
        detail_layout.addWidget(self.detail_lbl)
        left_layout.addWidget(self.detail_frame)

        splitter.addWidget(left_widget)

        # Right side: PDF Canvas
        self.pdf_canvas = PdfCanvas()
        splitter.addWidget(self.pdf_canvas)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def refresh(self, project: Project):
        self.current_project = project
        self.flagged_records.clear()

        # Gather records with low confidence (< 0.90) or flagged
        for ds_name, ds in project.datasets.items():
            for rec in ds.records:
                is_low_conf = rec.provenance.confidence < 0.90
                is_flagged = rec.is_flagged_for_review
                if (is_low_conf or is_flagged) and not rec.review_dismissed:
                    reason = "Low Confidence" if is_low_conf else "Validation Flag"
                    self.flagged_records.append((ds_name, rec, reason))

        self.count_lbl.setText(f"{len(self.flagged_records)} records pending review")
        self.queue_table.blockSignals(True)
        self.queue_table.setRowCount(len(self.flagged_records))

        for row_idx, (ds_name, rec, reason) in enumerate(self.flagged_records):
            self.queue_table.setItem(row_idx, 0, QTableWidgetItem(ds_name))
            self.queue_table.setItem(row_idx, 1, QTableWidgetItem(rec.provenance.source_document))
            self.queue_table.setItem(row_idx, 2, QTableWidgetItem(f"Page {rec.provenance.source_page}"))
            self.queue_table.setItem(row_idx, 3, QTableWidgetItem(f"{rec.provenance.confidence*100:.0f}%"))
            self.queue_table.setItem(row_idx, 4, QTableWidgetItem(reason))

        self.queue_table.blockSignals(False)

        if self.flagged_records:
            self.queue_table.selectRow(0)
        else:
            self.detail_lbl.setText("No records require review! All extractions meet high confidence thresholds.")

    def on_queue_item_selected(self):
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.flagged_records):
            return

        ds_name, rec, reason = self.flagged_records[row]

        # Display details
        lines = [f"<b>Dataset:</b> {ds_name} | <b>Extraction Method:</b> {rec.provenance.extraction_method} | <b>Confidence:</b> {rec.provenance.confidence*100:.0f}%"]
        for fname, cell in rec.cells.items():
            lines.append(f"<b>{fname}:</b> {cell.normalized_value} (raw: <i>{cell.raw_value}</i>)")
        self.detail_lbl.setText("<br>".join(lines))

        # Jump PDF canvas to source page
        if self.current_project:
            for doc in self.current_project.documents.values():
                if doc.filename == rec.provenance.source_document:
                    self.pdf_canvas.load_document(doc.file_path, initial_page=rec.provenance.source_page)
                    break

    def accept_selected(self):
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.flagged_records):
            return

        ds_name, rec, reason = self.flagged_records[row]
        rec.provenance.status = RecordStatus.HUMAN_REVIEWED
        rec.is_flagged_for_review = False
        rec.review_dismissed = True
        rec.provenance.add_audit("Accepted in Human-in-the-Loop review queue")
        if self.current_project:
            self.current_project.save()

        self.refresh(self.current_project)
        self.record_updated.emit()

    def edit_selected(self):
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.flagged_records):
            return

        ds_name, rec, reason = self.flagged_records[row]
        field_names = list(rec.cells.keys())
        field, ok = QInputDialog.getItem(self, "Select Field to Edit", "Field:", field_names, 0, False)
        if ok and field:
            curr_val = str(rec.get_value(field, prefer_normalized=True) or "")
            new_val, ok2 = QInputDialog.getText(self, f"Edit {field}", f"New value for {field}:", text=curr_val)
            if ok2 and new_val:
                raw_v = rec.cells[field].raw_value
                rec.set_value(field, raw_v, new_val)
                rec.provenance.status = RecordStatus.HUMAN_REVIEWED
                rec.provenance.add_audit(f"Manually edited field '{field}' to '{new_val}'")
                rec.is_flagged_for_review = False
                rec.review_dismissed = True
                if self.current_project:
                    self.current_project.save()
                self.refresh(self.current_project)
                self.record_updated.emit()

    def reject_selected(self):
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self.flagged_records):
            return

        ds_name, rec, reason = self.flagged_records[row]
        # Remove from dataset
        if self.current_project and ds_name in self.current_project.datasets:
            ds = self.current_project.datasets[ds_name]
            ds.records = [r for r in ds.records if r.id != rec.id]
            self.current_project.save()
            QMessageBox.information(self, "Record Rejected", "Record has been discarded from the dataset.")

        self.refresh(self.current_project)
        self.record_updated.emit()
