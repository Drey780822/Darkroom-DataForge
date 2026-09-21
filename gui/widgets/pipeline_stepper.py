from __future__ import annotations
from typing import Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QWidget,
)
from core.pipeline import PipelineStage, StageStatus


class StageStepWidget(QFrame):
    def __init__(self, stage: PipelineStage, label: str, parent=None):
        super().__init__(parent)
        self.stage = stage
        self.label_text = label
        self.status = StageStatus.PENDING
        self.duration = 0.0
        self.setObjectName("SecondaryCard")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self.title_lbl = QLabel(self.label_text)
        self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #8E8E93;")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel("PENDING")
        self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #5C5C62; padding: 2px 6px; border-radius: 4px; background: rgba(255, 255, 255, 0.04);")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_lbl)

        self.time_lbl = QLabel("-")
        self.time_lbl.setStyleSheet("font-size: 9px; color: #5C5C62;")
        self.time_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_lbl)

    def set_status(self, status: StageStatus, duration: float = 0.0):
        self.status = status
        self.duration = duration

        if duration > 0:
            self.time_lbl.setText(f"{duration:.1f}s")
        else:
            self.time_lbl.setText("-")

        if status == StageStatus.RUNNING:
            self.status_lbl.setText("RUNNING")
            self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #FFFFFF; background: rgba(255, 255, 255, 0.14); border: 1px solid rgba(255, 255, 255, 0.25); padding: 2px 6px; border-radius: 4px;")
            self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #EDEDED;")
        elif status == StageStatus.COMPLETE:
            self.status_lbl.setText("COMPLETE")
            self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #10A37F; background: rgba(16, 163, 127, 0.12); border: 1px solid rgba(16, 163, 127, 0.25); padding: 2px 6px; border-radius: 4px;")
            self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #EDEDED;")
        elif status == StageStatus.WARNING:
            self.status_lbl.setText("WARNING")
            self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #F5A623; background: rgba(245, 166, 35, 0.12); border: 1px solid rgba(245, 166, 35, 0.25); padding: 2px 6px; border-radius: 4px;")
            self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #EDEDED;")
        elif status == StageStatus.FAILED:
            self.status_lbl.setText("FAILED")
            self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #E5534B; background: rgba(229, 83, 75, 0.12); border: 1px solid rgba(229, 83, 75, 0.25); padding: 2px 6px; border-radius: 4px;")
            self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #E5534B;")
        else:
            self.status_lbl.setText("PENDING")
            self.status_lbl.setStyleSheet("font-size: 9px; font-weight: 600; color: #5C5C62; background: rgba(255, 255, 255, 0.04); padding: 2px 6px; border-radius: 4px;")
            self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #8E8E93;")


class PipelineStepper(QFrame):
    """Horizontal stepper component showing the live status of all 8 pipeline stages."""

    STAGES = [
        (PipelineStage.INGEST, "1. INGEST"),
        (PipelineStage.INSPECT, "2. INSPECT"),
        (PipelineStage.CLASSIFY, "3. CLASSIFY"),
        (PipelineStage.EXTRACT, "4. EXTRACT"),
        (PipelineStage.NORMALIZE, "5. NORMALIZE"),
        (PipelineStage.VALIDATE, "6. VALIDATE"),
        (PipelineStage.REVIEW, "7. REVIEW"),
        (PipelineStage.EXPORT, "8. EXPORT"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.step_widgets: Dict[PipelineStage, StageStepWidget] = {}
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        for stage, label in self.STAGES:
            step = StageStepWidget(stage, label, self)
            self.step_widgets[stage] = step
            layout.addWidget(step)

    def update_stage(self, stage: PipelineStage, status: StageStatus, duration: float = 0.0):
        if stage in self.step_widgets:
            self.step_widgets[stage].set_status(status, duration)

    def reset_all(self):
        for step in self.step_widgets.values():
            step.set_status(StageStatus.PENDING, 0.0)
