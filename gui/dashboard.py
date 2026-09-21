from __future__ import annotations
from typing import Optional
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
)
from core.project import Project


class KpiCard(QFrame):
    def __init__(self, title: str, initial_value: str = "0", color: str = "#EDEDED", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("CardTitle")
        layout.addWidget(t_lbl)

        self.v_lbl = QLabel(initial_value)
        self.v_lbl.setObjectName("CardValue")
        self.v_lbl.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 600; letter-spacing: -0.5px;")
        layout.addWidget(self.v_lbl)

    def set_value(self, val: str):
        self.v_lbl.setText(val)


class DashboardView(QWidget):
    """Overview dashboard showing key performance indicators, recent documents, and quick actions."""

    create_project_requested = Signal()
    switch_workspace_requested = Signal()
    load_demo_requested = Signal()
    ingest_requested = Signal()
    run_pipeline_requested = Signal()
    run_selected_requested = Signal(list)
    view_document_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header with title and quick action buttons
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("Overview")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.4px;")
        header_text.addWidget(title)

        self.project_sub = QLabel("Active Project: None")
        self.project_sub.setStyleSheet("font-size: 12px; color: #8E8E93;")
        header_text.addWidget(self.project_sub)
        header_layout.addLayout(header_text)

        header_layout.addStretch()

        self.btn_load_demo = QPushButton("Load Demo")
        self.btn_load_demo.setObjectName("NavyButton")
        self.btn_load_demo.setToolTip("Generate synthetic fixtures and load the TVET Qualifications demo project.")
        self.btn_load_demo.clicked.connect(self.load_demo_requested.emit)
        header_layout.addWidget(self.btn_load_demo)

        self.btn_switch_ws = QPushButton("Switch Workspace")
        self.btn_switch_ws.setObjectName("NavyButton")
        self.btn_switch_ws.clicked.connect(self.switch_workspace_requested.emit)
        header_layout.addWidget(self.btn_switch_ws)

        self.btn_ingest = QPushButton("Import PDFs")
        self.btn_ingest.setObjectName("NavyButton")
        self.btn_ingest.clicked.connect(self.ingest_requested.emit)
        header_layout.addWidget(self.btn_ingest)

        self.btn_run = QPushButton("Run Pipeline")
        self.btn_run.setObjectName("SuccessButton")
        self.btn_run.clicked.connect(self.run_pipeline_requested.emit)
        header_layout.addWidget(self.btn_run)

        layout.addLayout(header_layout)

        # 4 KPI Cards
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        self.kpi_docs = KpiCard("DOCUMENTS PROCESSED", "0", color="#EDEDED")
        kpi_grid.addWidget(self.kpi_docs, 0, 0)

        self.kpi_records = KpiCard("RECORDS EXTRACTED", "0", color="#EDEDED")
        kpi_grid.addWidget(self.kpi_records, 0, 1)

        self.kpi_validation = KpiCard("VALIDATION ISSUES", "0", color="#F5A623")
        kpi_grid.addWidget(self.kpi_validation, 0, 2)

        self.kpi_datasets = KpiCard("DATASETS GENERATED", "0", color="#10A37F")
        kpi_grid.addWidget(self.kpi_datasets, 0, 3)

        layout.addLayout(kpi_grid)

        # Lower section: Recent documents table with granular selection
        docs_card = QFrame()
        docs_card.setObjectName("Card")
        docs_layout = QVBoxLayout(docs_card)
        docs_layout.setContentsMargins(20, 18, 20, 18)
        docs_layout.setSpacing(12)

        docs_top = QHBoxLayout()
        docs_header = QLabel("RECENT DOCUMENTS IN WORKSPACE")
        docs_header.setObjectName("CardTitle")
        docs_top.addWidget(docs_header)
        docs_top.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setFixedHeight(26)
        self.btn_select_all.clicked.connect(self.select_all_docs)
        docs_top.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setFixedHeight(26)
        self.btn_deselect_all.clicked.connect(self.deselect_all_docs)
        docs_top.addWidget(self.btn_deselect_all)

        self.btn_run_selected = QPushButton("Run Selected")
        self.btn_run_selected.setObjectName("SuccessButton")
        self.btn_run_selected.setFixedHeight(26)
        self.btn_run_selected.clicked.connect(self.on_run_selected_clicked)
        docs_top.addWidget(self.btn_run_selected)
        docs_top.addWidget(self.btn_run_selected)

        docs_layout.addLayout(docs_top)

        self.doc_table = QTableWidget(0, 6)
        self.doc_table.setHorizontalHeaderLabels(["Select", "Filename", "Pages", "Classified Type", "Extraction Strategy", "Status"])
        self.doc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.doc_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.doc_table.verticalHeader().setVisible(False)
        docs_layout.addWidget(self.doc_table)

        layout.addWidget(docs_card)

    def select_all_docs(self):
        for r in range(self.doc_table.rowCount()):
            item = self.doc_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def deselect_all_docs(self):
        for r in range(self.doc_table.rowCount()):
            item = self.doc_table.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def get_selected_document_ids(self) -> list:
        if not self.current_project:
            return []
        selected = []
        docs = list(self.current_project.documents.values())
        for r in range(min(self.doc_table.rowCount(), len(docs))):
            item = self.doc_table.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(docs[r].id)
        return selected

    def on_run_selected_clicked(self):
        selected_ids = self.get_selected_document_ids()
        if selected_ids:
            self.run_selected_requested.emit(selected_ids)
        else:
            self.run_pipeline_requested.emit()

    def refresh(self, project: Project):
        self.current_project = project
        self.project_sub.setText(f"Active Project: {project.metadata.name} ({project.metadata.run_count} runs)")

        # Update KPIs
        doc_count = len(project.documents)
        record_count = sum(ds.record_count for ds in project.datasets.values())
        issue_count = project.validation_summary.total_issues if project.validation_summary else 0
        dataset_count = len(project.datasets)

        self.kpi_docs.set_value(f"{doc_count}")
        self.kpi_records.set_value(f"{record_count:,}")
        self.kpi_validation.set_value(f"{issue_count} issues")
        self.kpi_datasets.set_value(f"{dataset_count}")

        # Update table
        self.doc_table.setRowCount(len(project.documents))
        for row_idx, doc in enumerate(project.documents.values()):
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Checked)
            self.doc_table.setItem(row_idx, 0, chk_item)

            self.doc_table.setItem(row_idx, 1, QTableWidgetItem(doc.filename))
            pages_val = str(doc.inspection.page_count) if doc.inspection else "-"
            self.doc_table.setItem(row_idx, 2, QTableWidgetItem(pages_val))

            type_val = doc.effective_document_type.label if doc.effective_document_type else "Pending"
            self.doc_table.setItem(row_idx, 3, QTableWidgetItem(type_val))

            strat_val = doc.effective_extractor or "Auto"
            self.doc_table.setItem(row_idx, 4, QTableWidgetItem(strat_val))

            status_val = doc.status.value
            self.doc_table.setItem(row_idx, 5, QTableWidgetItem(status_val))
