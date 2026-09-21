from __future__ import annotations
from typing import Optional, List
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFrame,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QDialog,
    QFormLayout,
    QScrollArea,
)
from models.dataset import Dataset
from core.project import Project
from exporters import CsvExporter, JsonExporter, ExcelExporter, SqlExporter
from .widgets.spreadsheet_table import SpreadsheetTable
from .widgets.quality_gauge import QualityGauge


class AddRecordDialog(QDialog):
    """Modal dialog for appending a typed record to an active dataset."""

    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add Record — {dataset.metadata.display_name}")
        self.resize(500, 420)
        self.inputs = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        lbl = QLabel(f"Enter values for new record in '{dataset.metadata.display_name}':")
        lbl.setStyleSheet("font-weight: 700; color: #F8FAFC; font-size: 13px;")
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(10)

        for col in dataset.columns:
            le = QLineEdit()
            req_str = " (Required)" if col.required else ""
            le.setPlaceholderText(f"{col.data_type.value}{req_str}")
            col_lbl = QLabel(f"{col.display_name or col.name}:")
            col_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600;")
            form_layout.addRow(col_lbl, le)
            self.inputs[col.name] = le

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Add Record")
        save_btn.setObjectName("SuccessButton")
        save_btn.clicked.connect(self.accept)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def get_values(self) -> dict:
        return {k: le.text().strip() for k, le in self.inputs.items()}


class DatasetView(QWidget):
    """Dataset exploration view with spreadsheet viewer, schema inspector, quality gauge, CRUD operations, and exports."""

    view_source_requested = Signal(str, int)  # (document_filename, page_number)
    dataset_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.current_dataset: Optional[Dataset] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Top Bar: Dataset picker, search, and export actions
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        ds_lbl = QLabel("Dataset:")
        ds_lbl.setStyleSheet("font-weight: 600; color: #EDEDED;")
        top_bar.addWidget(ds_lbl)

        self.ds_combo = QComboBox()
        self.ds_combo.setMinimumWidth(220)
        self.ds_combo.currentIndexChanged.connect(self.on_dataset_selected)
        top_bar.addWidget(self.ds_combo)

        top_bar.addSpacing(15)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter records...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        top_bar.addStretch()

        # Export buttons
        self.btn_export_csv = QPushButton("CSV")
        self.btn_export_csv.clicked.connect(lambda: self.export_current("csv"))
        top_bar.addWidget(self.btn_export_csv)

        self.btn_export_json = QPushButton("JSON")
        self.btn_export_json.clicked.connect(lambda: self.export_current("json"))
        top_bar.addWidget(self.btn_export_json)

        self.btn_export_excel = QPushButton("Excel")
        self.btn_export_excel.clicked.connect(lambda: self.export_current("excel"))
        top_bar.addWidget(self.btn_export_excel)

        self.btn_export_sql = QPushButton("PostgreSQL / Supabase")
        self.btn_export_sql.setObjectName("NavyButton")
        self.btn_export_sql.clicked.connect(lambda: self.export_current("sql"))
        top_bar.addWidget(self.btn_export_sql)

        layout.addLayout(top_bar)

        # CRUD Bar: Record and Dataset operations
        crud_bar = QHBoxLayout()
        crud_bar.setSpacing(8)

        self.btn_add_rec = QPushButton("Add Record")
        self.btn_add_rec.setObjectName("NavyButton")
        self.btn_add_rec.setFixedHeight(28)
        self.btn_add_rec.clicked.connect(self.on_add_record_clicked)
        crud_bar.addWidget(self.btn_add_rec)

        self.btn_del_rec = QPushButton("Delete Record")
        self.btn_del_rec.setFixedHeight(28)
        self.btn_del_rec.clicked.connect(self.on_delete_record_clicked)
        crud_bar.addWidget(self.btn_del_rec)

        crud_bar.addSpacing(15)

        self.btn_del_ds = QPushButton("Delete Dataset")
        self.btn_del_ds.setObjectName("DangerButton")
        self.btn_del_ds.setFixedHeight(28)
        self.btn_del_ds.clicked.connect(self.on_delete_dataset_clicked)
        crud_bar.addWidget(self.btn_del_ds)

        self.btn_clear_ds = QPushButton("Clear All")
        self.btn_clear_ds.setObjectName("DangerButton")
        self.btn_clear_ds.setFixedHeight(28)
        self.btn_clear_ds.clicked.connect(self.on_clear_all_datasets_clicked)
        crud_bar.addWidget(self.btn_clear_ds)

        crud_bar.addStretch()
        layout.addLayout(crud_bar)

        # Main splitter: Left is spreadsheet and schema table, Right is Quality Gauge
        splitter = QSplitter(Qt.Horizontal)

        # Left Container
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Spreadsheet
        self.spreadsheet = SpreadsheetTable()
        self.spreadsheet.view_source_requested.connect(self.view_source_requested.emit)
        self.spreadsheet.record_edited.connect(self.on_record_edited)
        left_layout.addWidget(self.spreadsheet)

        # Bottom Schema Details
        schema_frame = QFrame()
        schema_frame.setObjectName("Card")
        schema_layout = QVBoxLayout(schema_frame)
        schema_layout.setContentsMargins(12, 10, 12, 10)
        schema_layout.setSpacing(6)

        schema_title = QLabel("DETECTED SCHEMA & CANONICAL MAPPINGS")
        schema_title.setObjectName("CardTitle")
        schema_layout.addWidget(schema_title)

        self.schema_table = QTableWidget(0, 5)
        self.schema_table.setFixedHeight(120)
        self.schema_table.setHorizontalHeaderLabels(["Field (snake_case)", "Original Source Header", "Type", "Required", "Key"])
        self.schema_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.schema_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.schema_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.schema_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.schema_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.schema_table.verticalHeader().setVisible(False)
        schema_layout.addWidget(self.schema_table)

        left_layout.addWidget(schema_frame)
        splitter.addWidget(left_box)

        # Right Container: Quality Gauge & Relationship Info
        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        self.quality_gauge = QualityGauge()
        right_layout.addWidget(self.quality_gauge)

        # Relationship Card
        self.rel_frame = QFrame()
        self.rel_frame.setObjectName("Card")
        rel_layout = QVBoxLayout(self.rel_frame)
        rel_layout.setContentsMargins(14, 12, 14, 12)
        rel_layout.setSpacing(6)

        rel_title = QLabel("DETECTED ENTITY RELATIONSHIPS")
        rel_title.setObjectName("CardTitle")
        rel_layout.addWidget(rel_title)

        self.rel_label = QLabel("No 1:N relations detected.")
        self.rel_label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.rel_label.setWordWrap(True)
        rel_layout.addWidget(self.rel_label)

        right_layout.addWidget(self.rel_frame)
        right_layout.addStretch()

        splitter.addWidget(right_box)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def refresh(self, project: Project):
        self.current_project = project
        self.ds_combo.blockSignals(True)
        self.ds_combo.clear()

        for name in project.datasets.keys():
            self.ds_combo.addItem(name)

        self.ds_combo.blockSignals(False)

        if project.datasets:
            first_name = list(project.datasets.keys())[0]
            self.load_dataset(project.datasets[first_name])
        else:
            self.spreadsheet.clear()
            self.schema_table.clear()

        # Update relationships
        if project.relationships:
            lines = []
            for r in project.relationships:
                lines.append(f"• <b>{r.parent_dataset}</b> -> 1:N -> <b>{r.child_dataset}</b> (FK: <code>{r.foreign_key}</code>)")
            self.rel_label.setText("<br>".join(lines))
        else:
            self.rel_label.setText("No 1:N relations detected.")

    def on_dataset_selected(self, idx: int):
        if not self.current_project:
            return
        name = self.ds_combo.currentText()
        if name in self.current_project.datasets:
            self.load_dataset(self.current_project.datasets[name])

    def load_dataset(self, dataset: Dataset):
        self.current_dataset = dataset
        self.spreadsheet.load_dataset(dataset, filter_text=self.search_input.text())

        # Update schema table
        self.schema_table.setRowCount(len(dataset.columns))
        for r_idx, col in enumerate(dataset.columns):
            self.schema_table.setItem(r_idx, 0, QTableWidgetItem(col.name))
            self.schema_table.setItem(r_idx, 1, QTableWidgetItem(col.source_header or col.display_name))
            self.schema_table.setItem(r_idx, 2, QTableWidgetItem(col.data_type.value))
            self.schema_table.setItem(r_idx, 3, QTableWidgetItem("Yes" if col.required else "No"))
            key_val = "PK" if col.is_primary_key else ("FK" if col.is_foreign_key else "-")
            self.schema_table.setItem(r_idx, 4, QTableWidgetItem(key_val))

        # Update quality gauge
        if dataset.metadata.quality:
            self.quality_gauge.update_metrics(dataset.metadata.quality)

    def on_search_changed(self, text: str):
        if self.current_dataset:
            self.spreadsheet.load_dataset(self.current_dataset, filter_text=text)

    def on_add_record_clicked(self):
        if not self.current_dataset or not self.current_project:
            QMessageBox.information(self, "No Dataset", "Please select or create an active dataset first.")
            return

        dialog = AddRecordDialog(self.current_dataset, parent=self)
        if dialog.exec():
            vals = dialog.get_values()
            rec = self.current_project.add_record_to_dataset(self.current_dataset.metadata.name, vals)
            if rec:
                self.load_dataset(self.current_project.datasets[self.current_dataset.metadata.name])
                self.dataset_modified.emit()
                QMessageBox.information(self, "Record Added", f"Successfully added record to '{self.current_dataset.metadata.display_name}'.")

    def on_delete_record_clicked(self):
        if not self.current_dataset or not self.current_project:
            return

        selected_rec = self.spreadsheet.get_selected_record()
        if not selected_rec:
            QMessageBox.information(self, "Select Record", "Please click on a row in the spreadsheet table to select it for deletion.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Record",
            f"Are you sure you want to delete the selected record (ID: {selected_rec.id[:8]}...)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self.current_project.remove_record_from_dataset(self.current_dataset.metadata.name, selected_rec.id)
            if success:
                self.load_dataset(self.current_project.datasets[self.current_dataset.metadata.name])
                self.dataset_modified.emit()

    def on_delete_dataset_clicked(self):
        if not self.current_dataset or not self.current_project:
            return

        ds_name = self.current_dataset.metadata.name
        reply = QMessageBox.question(
            self,
            "Delete Dataset",
            f"Are you sure you want to delete dataset '{ds_name}' and remove its persisted files?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.current_project.delete_dataset(ds_name)
            self.current_dataset = None
            self.refresh(self.current_project)
            self.dataset_modified.emit()

    def on_clear_all_datasets_clicked(self):
        if not self.current_project or not self.current_project.datasets:
            return

        reply = QMessageBox.warning(
            self,
            "Clear All Datasets",
            "Are you sure you want to permanently delete ALL datasets from this project? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.current_project.clear_all_datasets()
            self.current_dataset = None
            self.refresh(self.current_project)
            self.dataset_modified.emit()

    def on_record_edited(self, rec_id: str, field_name: str, new_val: str):
        if self.current_project and self.current_dataset:
            self.current_project.update_cell_value(self.current_dataset.metadata.name, rec_id, field_name, new_val)
            self.dataset_modified.emit()

    def export_current(self, fmt: str):
        if not self.current_dataset or not self.current_project:
            return

        export_dir = self.current_project.workspace.exports_dir
        if fmt == "csv":
            path = CsvExporter().export_dataset(self.current_dataset, str(export_dir / f"{self.current_dataset.metadata.name}.csv"))
            QMessageBox.information(self, "Exported CSV", f"Saved to:\n{path}")
        elif fmt == "json":
            path = JsonExporter().export_dataset(self.current_dataset, str(export_dir / f"{self.current_dataset.metadata.name}.json"))
            QMessageBox.information(self, "Exported JSON", f"Saved to:\n{path}")
        elif fmt == "excel":
            paths = ExcelExporter().export_all(list(self.current_project.datasets.values()), str(export_dir))
            QMessageBox.information(self, "Exported Excel", f"Saved to:\n{paths[0]}")
        elif fmt == "sql":
            paths = SqlExporter().export_all(list(self.current_project.datasets.values()), str(export_dir))
            QMessageBox.information(self, "Exported PostgreSQL Schema", f"Saved to:\n{paths[0]}")
