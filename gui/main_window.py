from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QFrame,
    QLabel,
    QPushButton,
    QStatusBar,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QGraphicsOpacityEffect,
)
from core.project import Project
from .styles import DARKROOM_STYLE
from .dashboard import DashboardView
from .document_viewer import DocumentView
from .extraction_view import ExtractionView
from .dataset_view import DatasetView
from .validation_view import ValidationView
from .review_queue_view import ReviewQueueView
from .comparison_view import ComparisonView
from .settings_view import SettingsView


class MainWindow(QMainWindow):
    """Primary application window for Darkroom DataForge data engineering platform."""

    def __init__(self, workspace_dir: str = "./dataforge_workspace"):
        super().__init__()
        self.setWindowTitle("Darkroom DataForge — Wits–merSETA Darkroom")
        self.resize(1340, 840)
        self.setMinimumSize(1080, 680)

        self.project: Optional[Project] = None
        self.default_workspace = workspace_dir

        self.init_project(workspace_dir)
        self.init_ui()
        self.apply_theme()
        self.refresh_all_views()

    def init_project(self, path_str: str):
        p = Path(path_str).resolve()
        p.mkdir(parents=True, exist_ok=True)
        self.project = Project(workspace_path=str(p), name=p.name)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # Left Sidebar
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(8)

        # Brand header
        brand_box = QVBoxLayout()
        brand_box.setSpacing(3)

        title = QLabel("DARKROOM\nDATAFORGE")
        title.setObjectName("BrandTitle")
        brand_box.addWidget(title)

        org_label = QLabel("WITS–merSETA DARKROOM")
        org_label.setObjectName("BrandSubtitle")
        brand_box.addWidget(org_label)

        platform_label = QLabel("DATASET GENERATION PLATFORM")
        platform_label.setStyleSheet("font-size: 8px; color: #64748B; font-weight: 700; letter-spacing: 0.5px;")
        brand_box.addWidget(platform_label)

        side_layout.addLayout(brand_box)
        side_layout.addSpacing(15)

        # Navigation Buttons
        self.nav_buttons = []

        nav_items = [
            ("Overview", 0),
            ("Documents", 1),
            ("Pipeline", 2),
            ("Datasets", 3),
            ("Validation", 4),
            ("Review Queue", 5),
            ("Comparison", 6),
            ("Settings", 7),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=index: self.switch_view(idx))
            self.nav_buttons.append(btn)
            side_layout.addWidget(btn)

        self.nav_buttons[0].setChecked(True)

        side_layout.addStretch()

        # Workspace switcher button
        self.btn_switch_ws = QPushButton("Switch Workspace")
        self.btn_switch_ws.setObjectName("NavyButton")
        self.btn_switch_ws.clicked.connect(self.switch_workspace_dialog)
        side_layout.addWidget(self.btn_switch_ws)

        # Bottom Info
        side_layout.addSpacing(6)
        self.ws_lbl = QLabel(f"Project: {self.project.metadata.name}")
        self.ws_lbl.setStyleSheet("font-size: 10px; color: #8E8E93;")
        side_layout.addWidget(self.ws_lbl)

        ver_lbl = QLabel("v1.0.0 • Local Workstation")
        ver_lbl.setStyleSheet("font-size: 9px; color: #5C5C62;")
        side_layout.addWidget(ver_lbl)

        main_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # Center Stacked Widget
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        self.view_dashboard = DashboardView()
        self.view_documents = DocumentView()
        self.view_extraction = ExtractionView()
        self.view_dataset = DatasetView()
        self.view_validation = ValidationView()
        self.view_review = ReviewQueueView()
        self.view_comparison = ComparisonView()
        self.view_settings = SettingsView()

        self.stack.addWidget(self.view_dashboard)    # 0
        self.stack.addWidget(self.view_documents)    # 1
        self.stack.addWidget(self.view_extraction)   # 2
        self.stack.addWidget(self.view_dataset)      # 3
        self.stack.addWidget(self.view_validation)   # 4
        self.stack.addWidget(self.view_review)       # 5
        self.stack.addWidget(self.view_comparison)   # 6
        self.stack.addWidget(self.view_settings)     # 7

        main_layout.addWidget(self.stack)

        # Connect inter-view signals
        self.view_dashboard.switch_workspace_requested.connect(self.switch_workspace_dialog)
        self.view_dashboard.load_demo_requested.connect(self.on_load_demo)
        self.view_dashboard.ingest_requested.connect(lambda: self.switch_view(1))
        self.view_dashboard.run_pipeline_requested.connect(lambda: self.switch_view(2))
        self.view_dashboard.run_selected_requested.connect(self.on_run_pipeline_for_documents)

        self.view_documents.documents_imported.connect(self.on_documents_imported)
        self.view_documents.process_selected_requested.connect(self.on_run_pipeline_for_documents)
        self.view_documents.delete_documents_requested.connect(self.on_delete_documents)
        self.view_documents.clear_all_documents_requested.connect(self.on_clear_all_documents)
        self.view_documents.reinspect_selected_requested.connect(self.on_reinspect_documents)

        self.view_extraction.pipeline_completed.connect(self.on_pipeline_completed)

        self.view_dataset.view_source_requested.connect(self.jump_to_source_page)
        self.view_dataset.dataset_modified.connect(self.refresh_all_views)
        self.view_review.record_updated.connect(self.on_review_updated)
        self.view_validation.auto_fix_applied.connect(self.refresh_all_views)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready • Darkroom DataForge")

    def apply_theme(self):
        self.setStyleSheet(DARKROOM_STYLE)

    def switch_view(self, index: int):
        if self.stack.currentIndex() == index:
            return

        target = self.stack.widget(index)
        self.stack.setCurrentIndex(index)
        for idx, btn in enumerate(self.nav_buttons):
            btn.setChecked(idx == index)

        # Notion / OpenAI minimalist fade transition
        effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(160)
        anim.setStartValue(0.10)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._current_anim = anim

    def refresh_all_views(self):
        if not self.project:
            return

        self.ws_lbl.setText(f"Project: {self.project.metadata.name}")
        self.view_dashboard.refresh(self.project)
        self.view_documents.refresh(self.project)
        self.view_extraction.refresh(self.project)
        self.view_dataset.refresh(self.project)
        self.view_validation.refresh(self.project)
        self.view_review.refresh(self.project)
        self.view_comparison.refresh(self.project)

    def on_documents_imported(self, file_paths: list):
        if not self.project:
            return

        for p in file_paths:
            try:
                self.project.add_document(p)
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Could not import {Path(p).name}: {e}")

        self.refresh_all_views()
        self.status_bar.showMessage(f"Imported {len(file_paths)} document(s). Ready to inspect/extract.")

    def on_run_pipeline_for_documents(self, doc_ids: list):
        self.switch_view(2)  # Switch to Pipeline Execution view
        self.view_extraction.start_pipeline(document_ids=doc_ids)

    def on_delete_documents(self, doc_ids: list):
        if not self.project:
            return

        deleted_count = 0
        for did in doc_ids:
            if self.project.remove_document(did, delete_physical_file=True):
                deleted_count += 1

        self.refresh_all_views()
        self.status_bar.showMessage(f"Deleted {deleted_count} document(s) and associated files.")

    def on_clear_all_documents(self):
        if not self.project:
            return

        count = self.project.clear_all_documents(delete_physical_files=True)
        self.refresh_all_views()
        self.status_bar.showMessage(f"Cleared all {count} document(s) from workspace.")

    def on_reinspect_documents(self, doc_ids: list):
        if not self.project:
            return

        from core.inspector import DocumentInspector
        from core.classifier import DocumentClassifier
        inspector = DocumentInspector()
        classifier = DocumentClassifier()

        for did in doc_ids:
            doc = self.project.get_document_by_id(did)
            if doc:
                try:
                    doc.inspection = inspector.inspect(doc.file_path)
                    doc.classification = classifier.classify(doc)
                except Exception as e:
                    print(f"Error re-inspecting {doc.filename}: {e}")

        self.project.save()
        self.refresh_all_views()
        self.status_bar.showMessage(f"Re-inspected and re-classified {len(doc_ids)} document(s).")

    def on_pipeline_completed(self, result):
        self.refresh_all_views()
        self.status_bar.showMessage(f"Extraction completed: {result.manifest.total_records_extracted} records generated.")

    def on_review_updated(self):
        self.refresh_all_views()

    def jump_to_source_page(self, doc_filename: str, page_number: int):
        self.switch_view(1)  # Documents view
        self.view_documents.jump_to_document_page(doc_filename, page_number)
        self.status_bar.showMessage(f"Viewing source: {doc_filename} (Page {page_number})")

    def switch_workspace_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Project Workspace Directory")
        if folder:
            self.init_project(folder)
            self.refresh_all_views()
            self.status_bar.showMessage(f"Switched workspace to: {Path(folder).name}")

    def on_load_demo(self):
        try:
            from demo.demo_project import DemoProjectManager
            self.status_bar.showMessage("Generating synthetic demo project...")
            demo_proj = DemoProjectManager.setup_demo_project()
            self.project = demo_proj
            self.refresh_all_views()
            self.status_bar.showMessage("Demo project loaded successfully • TVET Qualifications Demo")
            QMessageBox.information(
                self,
                "Demo Project Loaded",
                "Successfully generated synthetic TVET qualifications, QLFS codebook, and OIHD report fixtures!\n\n"
                "You can now navigate to the Extraction View to run the pipeline or inspect the documents."
            )
        except Exception as e:
            QMessageBox.critical(self, "Demo Error", f"Failed to load demo project: {e}")

