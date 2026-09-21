from __future__ import annotations
import time
from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QObject, QRunnable, QThreadPool
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from core.pipeline import DataforgePipeline, PipelineStage, StageStatus, PipelineRunResult
from core.project import Project
from .widgets.pipeline_stepper import PipelineStepper
from .widgets.log_console import LogConsole


class WorkerSignals(QObject):
    progress = Signal(object, float, str)  # (PipelineStage, pct, message)
    log = Signal(str, str)                 # (level, message)
    finished = Signal(object)             # (PipelineRunResult)
    error = Signal(str)                   # (error_message)


class PipelineWorker(QRunnable):
    def __init__(self, pipeline: DataforgePipeline, document_ids: Optional[List[str]] = None):
        super().__init__()
        self.pipeline = pipeline
        self.document_ids = document_ids
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.pipeline.run_pipeline(
                document_ids=self.document_ids,
                progress_callback=lambda stage, pct, msg: self.signals.progress.emit(stage, pct, msg),
                log_callback=lambda lvl, msg: self.signals.log.emit(lvl, msg),
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class ExtractionView(QWidget):
    """Pipeline execution monitor with stage stepper, progress indicator, and streaming log console."""

    pipeline_completed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[Project] = None
        self.thread_pool = QThreadPool.globalInstance()
        self.is_running = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Pipeline Execution Engine")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        title_box.addWidget(title)

        subtitle = QLabel("Select documents to execute multi-stage extraction, reconstruction, normalization, and validation.")
        subtitle.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()

        self.btn_run_selected = QPushButton("▶ Run Pipeline (Selected)")
        self.btn_run_selected.setObjectName("SuccessButton")
        self.btn_run_selected.clicked.connect(self.on_run_selected)
        header.addWidget(self.btn_run_selected)

        self.btn_run_all = QPushButton("⏩ Run Pipeline (All)")
        self.btn_run_all.setObjectName("PrimaryButton")
        self.btn_run_all.clicked.connect(self.on_run_all)
        header.addWidget(self.btn_run_all)

        layout.addLayout(header)

        # Document Selection Queue Card
        queue_card = QFrame()
        queue_card.setObjectName("Card")
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(14, 10, 14, 10)
        queue_layout.setSpacing(6)

        q_top = QHBoxLayout()
        q_lbl = QLabel("DOCUMENT EXECUTION QUEUE")
        q_lbl.setObjectName("CardTitle")
        q_top.addWidget(q_lbl)
        q_top.addStretch()

        self.btn_sel_all = QPushButton("Select All")
        self.btn_sel_all.setFixedHeight(24)
        self.btn_sel_all.clicked.connect(self.select_all)
        q_top.addWidget(self.btn_sel_all)

        self.btn_desel_all = QPushButton("Deselect All")
        self.btn_desel_all.setFixedHeight(24)
        self.btn_desel_all.clicked.connect(self.deselect_all)
        q_top.addWidget(self.btn_desel_all)

        queue_layout.addLayout(q_top)

        self.table_queue = QTableWidget(0, 5)
        self.table_queue.setFixedHeight(110)
        self.table_queue.setHorizontalHeaderLabels(["Select", "Filename", "Pages", "Classified Strategy", "Status"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_queue.verticalHeader().setVisible(False)
        queue_layout.addWidget(self.table_queue)

        layout.addWidget(queue_card)

        # Pipeline Stepper
        self.stepper = PipelineStepper()
        layout.addWidget(self.stepper)

        # Progress bar card
        prog_card = QFrame()
        prog_card.setObjectName("Card")
        prog_layout = QVBoxLayout(prog_card)
        prog_layout.setContentsMargins(16, 12, 16, 12)
        prog_layout.setSpacing(8)

        status_line = QHBoxLayout()
        self.status_lbl = QLabel("Status: Ready to execute.")
        self.status_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #F8FAFC;")
        status_line.addWidget(self.status_lbl)

        status_line.addStretch()

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #D4AF37;")
        status_line.addWidget(self.pct_lbl)
        prog_layout.addLayout(status_line)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #172033;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #D4AF37;
                border-radius: 4px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        layout.addWidget(prog_card)

        # Log console
        self.log_console = LogConsole()
        layout.addWidget(self.log_console)

    def select_all(self):
        for r in range(self.table_queue.rowCount()):
            item = self.table_queue.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def deselect_all(self):
        for r in range(self.table_queue.rowCount()):
            item = self.table_queue.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def get_selected_document_ids(self) -> List[str]:
        if not self.current_project:
            return []
        selected = []
        docs = list(self.current_project.documents.values())
        for r in range(min(self.table_queue.rowCount(), len(docs))):
            item = self.table_queue.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                selected.append(docs[r].id)
        return selected

    def on_run_selected(self):
        selected = self.get_selected_document_ids()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please check at least one document in the queue to process.")
            return
        self.start_pipeline(document_ids=selected)

    def on_run_all(self):
        self.start_pipeline(document_ids=None)

    def refresh(self, project: Project):
        self.current_project = project
        self.table_queue.blockSignals(True)
        self.table_queue.setRowCount(len(project.documents))

        for row_idx, doc in enumerate(project.documents.values()):
            chk_item = QTableWidgetItem()
            chk_item.setCheckState(Qt.Checked)
            self.table_queue.setItem(row_idx, 0, chk_item)

            self.table_queue.setItem(row_idx, 1, QTableWidgetItem(doc.filename))
            pages_val = str(doc.inspection.page_count) if doc.inspection else "-"
            self.table_queue.setItem(row_idx, 2, QTableWidgetItem(pages_val))

            strat_val = doc.effective_extractor or "Auto"
            self.table_queue.setItem(row_idx, 3, QTableWidgetItem(strat_val))

            status_val = doc.status.value
            self.table_queue.setItem(row_idx, 4, QTableWidgetItem(status_val))

        self.table_queue.blockSignals(False)

    def start_pipeline(self, document_ids: Optional[List[str]] = None):
        if not self.current_project:
            return
        if self.is_running:
            return

        self.is_running = True
        self.btn_run_selected.setEnabled(False)
        self.btn_run_all.setEnabled(False)
        self.stepper.reset_all()
        self.progress_bar.setValue(0)

        target_desc = f"{len(document_ids)} selected document(s)" if document_ids is not None else "all ingested documents"
        self.status_lbl.setText(f"Status: Initializing extraction pipeline for {target_desc}...")
        self.log_console.append_log("INFO", f"Starting pipeline execution on {target_desc} for project '{self.current_project.metadata.name}'...")

        pipeline = DataforgePipeline(self.current_project)
        worker = PipelineWorker(pipeline, document_ids=document_ids)
        worker.signals.progress.connect(self.on_progress)
        worker.signals.log.connect(self.on_log)
        worker.signals.finished.connect(self.on_finished)
        worker.signals.error.connect(self.on_error)

        self.thread_pool.start(worker)

    def on_progress(self, stage: PipelineStage, pct: float, msg: str):
        int_pct = int(pct * 100)
        self.progress_bar.setValue(int_pct)
        self.pct_lbl.setText(f"{int_pct}%")
        self.status_lbl.setText(f"Stage {stage.value}: {msg}")
        self.stepper.update_stage(stage, StageStatus.RUNNING)

    def on_log(self, level: str, msg: str):
        self.log_console.append_log(level, msg)

    def on_finished(self, result: PipelineRunResult):
        self.is_running = False
        self.btn_run_selected.setEnabled(True)
        self.btn_run_all.setEnabled(True)
        self.progress_bar.setValue(100)
        self.pct_lbl.setText("100%")
        self.status_lbl.setText(f"Pipeline Complete: {result.manifest.total_records_extracted} records extracted.")

        # Update stepper with finished statuses
        for s_name, s_res in result.stages.items():
            try:
                st = PipelineStage(s_name)
                self.stepper.update_stage(st, s_res.status, s_res.duration_seconds)
            except:
                pass

        self.log_console.append_log("SUCCESS", f"Run {result.run_id} completed successfully across {len(result.datasets)} datasets.")
        self.pipeline_completed.emit(result)

    def on_error(self, err_msg: str):
        self.is_running = False
        self.btn_run_selected.setEnabled(True)
        self.btn_run_all.setEnabled(True)
        self.status_lbl.setText(f"Pipeline Failed: {err_msg}")
        self.log_console.append_log("ERROR", f"Pipeline aborted with exception: {err_msg}")
