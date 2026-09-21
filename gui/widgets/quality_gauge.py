from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
)
from models.dataset import DatasetQuality


class MetricBar(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        header_layout = QHBoxLayout()
        self.label_lbl = QLabel(label)
        self.label_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        header_layout.addWidget(self.label_lbl)

        header_layout.addStretch()

        self.val_lbl = QLabel("0%")
        self.val_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #F8FAFC;")
        header_layout.addWidget(self.val_lbl)
        layout.addLayout(header_layout)

        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: #172033;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #D4AF37;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.bar)

    def set_value(self, score: float):
        score_int = int(round(score))
        self.val_lbl.setText(f"{score:.1f}%")
        self.bar.setValue(score_int)
        
        # Color coding
        color = "#22C55E" if score >= 90 else ("#F59E0B" if score >= 70 else "#EF4444")
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #172033;
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)


class QualityGauge(QFrame):
    """Component displaying multidimensional dataset quality score and operational signals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top_layout = QHBoxLayout()
        title = QLabel("DATASET QUALITY")
        title.setObjectName("CardTitle")
        top_layout.addWidget(title)
        top_layout.addStretch()

        self.overall_badge = QLabel("--%")
        self.overall_badge.setStyleSheet("font-size: 24px; font-weight: 800; color: #D4AF37;")
        top_layout.addWidget(self.overall_badge)
        layout.addLayout(top_layout)

        # Operational metrics breakdown
        self.bar_extraction = MetricBar("Extraction Quality")
        layout.addWidget(self.bar_extraction)

        self.bar_completeness = MetricBar("Completeness (Non-Null Ratio)")
        layout.addWidget(self.bar_completeness)

        self.bar_consistency = MetricBar("Schema & Type Consistency")
        layout.addWidget(self.bar_consistency)

        self.bar_validation = MetricBar("Rule Validation Compliance")
        layout.addWidget(self.bar_validation)

        notice = QLabel("* Operational indicator; not proof of correctness.")
        notice.setStyleSheet("font-size: 10px; color: #64748B; font-style: italic;")
        layout.addWidget(notice)

    def update_metrics(self, quality: DatasetQuality):
        score = quality.overall_score
        self.overall_badge.setText(f"{score:.1f}%")
        color = "#22C55E" if score >= 90 else ("#F59E0B" if score >= 70 else "#EF4444")
        self.overall_badge.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {color};")

        self.bar_extraction.set_value(quality.extraction_score)
        self.bar_completeness.set_value(quality.completeness_score)
        self.bar_consistency.set_value(quality.consistency_score)
        self.bar_validation.set_value(quality.validation_score)
