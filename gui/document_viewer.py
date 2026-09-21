from __future__ import annotations
from typing import Optional, List
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
    QComboBox,
    QMessageBox,
)
from pathlib import Path
from models.document import DocumentMetadata, DocumentType
from core.project import Project
from .widgets.drag_drop_zone import DragDropZone
from .widgets.pdf_canvas import PdfCanvas


class DocumentView(QWidget):
    """Document ingestion, classification review, and side-by-side inspection view with full CRUD."""

    documents_imported = Signal(list)
    process_selected_requested = Signal(list)
    delete_documents_requested = Signal(list)
    clear_all_documents_requested = Signal()
    reinspect_selected_requested = Signal(list)
    strategy_override_changed = Signal(str, str, str)  # (doc_id, type, extractor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Document Ingestion & Inspection")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        title_box.addWidget(title)

        subtitle = QLabel("Inspect PDF structure, verify classification, select documents, or manage ingestions.")
        subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()
        layout.addLayout(header)

        # Splitter: Left is ingestion & document table, Right is PDF canvas
        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Drag drop zone
        self.drop_zone = DragDropZone()
        self.drop_zone.files_selected.connect(self.on_files_dropped)
        left_layout.addWidget(self.drop_zone)

        # Documents table container
        tbl_frame = QFrame()
        tbl_frame.setObjectName("Card")
        tbl_layout = QVBoxLayout(tbl_frame)
        tbl_layout.setContentsMargins(12, 12, 12, 12)
        tbl_layout.setSpacing(8)

        # Action bar above table
        tbl_top = QHBoxLayout()
        tbl_title = QLabel("INGESTED DOCUMENTS")
        tbl_title.setObjectName("CardTitle")
        tbl_top.addWidget(tbl_title)
        tbl_top.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setFixedHeight(26)
        self.btn_select_all.clicked.connect(self.select_all)
        tbl_top.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setFixedHeight(26)
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        tbl_top.addWidget(self.btn_deselect_all)

        tbl_layout.addLayout(tbl_top)

        # Second row of action buttons
        actions_bar = QHBoxLayout()
        self.btn_process_sel = QPushButton("▶ Process Selected")
        self.btn_process_sel.setObjectName("SuccessButton")
        self.btn_process_sel.setFixedHeight(26)
        self.btn_process_sel.clicked.connect(self.on_process_selected)
        actions_bar.addWidget(self.btn_process_sel)

        self.btn_reinspect = QPushButton("🔄 Re-inspect")
        self.btn_reinspect.setObjectName("NavyButton")
        self.btn_reinspect.setFixedHeight(26)
        self.btn_reinspect.clicked.connect(self.on_reinspect_selected)
        actions_bar.addWidget(self.btn_reinspect)

        self.btn_delete_sel = QPushButton("🗑 Delete Selected")
        self.btn_delete_sel.setFixedHeight(26)
        self.btn_delete_sel.setStyleSheet("background-color: #3B1B1F; color: #EF4444; border: 1px solid #7F1D1D;")
        self.btn_delete_sel.clicked.connect(self.on_delete_selected)
        actions_bar.addWidget(self.btn_delete_sel)

        self.btn_clear_all = QPushButton("⚠ Clear All")
        self.btn_clear_all.setFixedHeight(26)
        self.btn_clear_all.setStyleSheet("background-color: #2D1515; color: #F87171; border: 1px solid #991B1B;")
        self.btn_clear_all.clicked.connect(self.on_clear_all)
        actions_bar.addWidget(self.btn_clear_all)

        tbl_layout.addLayout(actions_bar)

        self.doc_table = QTableWidget(0, 6)
        self.doc_table.setHorizontalHeaderLabels(["Select", "Filename", "Pages", "Classified Type", "Strategy", "Confidence"])
        self.doc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.doc_table.verticalHeader().setVisible(False)
        self.doc_table.itemSelectionChanged.connect(self.on_doc_selected)
        tbl_layout.addWidget(self.doc_table)

        left_layout.addWidget(tbl_frame)
        splitter.addWidget(left_widget)

        # Right side: PDF Canvas
        self.pdf_canvas = PdfCanvas()
        splitter.addWidget(self.pdf_canvas)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def on_files_dropped(self, files: List[str]):
        self.documents_imported.emit(files)

    def select_all(self):
        for r in range(self.doc_table.rowCount()):
            item = self.doc_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def deselect_all(self):
        for r in range(self.doc_table.rowCount()):
            item = self.doc_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def get_selected_document_ids(self) -> List[str]:
        if not self.current_project:
            return []
        selected = []
        docs = list(self.current_project.documents.values())
        for r in range(min(self.doc_table.rowCount(), len(docs))):
            item = self.doc_table.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(docs[r].id)
        return selected

    def on_process_selected(self):
        selected_ids = self.get_selected_document_ids()
        if not selected_ids:
            QMessageBox.information(self, "No Selection", "Please check at least one document to process.")
            return
        self.process_selected_requested.emit(selected_ids)

    def on_reinspect_selected(self):
        selected_ids = self.get_selected_document_ids()
        if not selected_ids:
            QMessageBox.information(self, "No Selection", "Please check at least one document to re-inspect.")
            return
        self.reinspect_selected_requested.emit(selected_ids)

    def on_delete_selected(self):
        selected_ids = self.get_selected_document_ids()
        if not selected_ids:
            QMessageBox.information(self, "No Selection", "Please check at least one document to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Ingested Documents",
            f"Are you sure you want to delete {len(selected_ids)} selected document(s) from the project and remove their files from disk?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_documents_requested.emit(selected_ids)

    def on_clear_all(self):
        if not self.current_project or not self.current_project.documents:
            return

        reply = QMessageBox.warning(
            self,
            "Clear All Ingestions",
            "Are you sure you want to delete ALL ingested documents and their files from the workspace? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_all_documents_requested.emit()

    def refresh(self, project: Project):
        self.current_project = project
        self.doc_table.blockSignals(True)
        self.doc_table.setRowCount(len(project.documents))

        docs = list(project.documents.values())
        for row_idx, doc in enumerate(docs):
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Checked)
            self.doc_table.setItem(row_idx, 0, chk_item)

            self.doc_table.setItem(row_idx, 1, QTableWidgetItem(doc.filename))

            pages_str = str(doc.inspection.page_count) if doc.inspection else "-"
            self.doc_table.setItem(row_idx, 2, QTableWidgetItem(pages_str))

            doc_type = doc.effective_document_type
            type_str = doc_type.label if doc_type else "Pending"
            self.doc_table.setItem(row_idx, 3, QTableWidgetItem(type_str))

            extractor = doc.effective_extractor or "pdf_tables"
            self.doc_table.setItem(row_idx, 4, QTableWidgetItem(extractor))

            conf_str = f"{doc.classification.confidence*100:.0f}%" if doc.classification else "-"
            self.doc_table.setItem(row_idx, 5, QTableWidgetItem(conf_str))

        self.doc_table.blockSignals(False)

        if docs and self.doc_table.currentRow() < 0:
            self.doc_table.selectRow(0)

    def on_doc_selected(self):
        row = self.doc_table.currentRow()
        if not self.current_project or row < 0:
            return

        docs = list(self.current_project.documents.values())
        if row < len(docs):
            selected_doc = docs[row]
            self.pdf_canvas.load_document(selected_doc.file_path, initial_page=1)

    def jump_to_document_page(self, doc_filename: str, page_number: int):
        if not self.current_project:
            return

        for row_idx, doc in enumerate(self.current_project.documents.values()):
            if doc.filename == doc_filename or Path(doc.file_path).name == doc_filename:
                self.doc_table.selectRow(row_idx)
                self.pdf_canvas.load_document(doc.file_path, initial_page=page_number)
                break
