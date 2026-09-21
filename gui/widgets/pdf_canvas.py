from __future__ import annotations
from typing import Optional
from pathlib import Path
import pymupdf
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QScrollArea,
)


class PdfCanvas(QFrame):
    """Integrated PDF viewer widget with page navigation, zoom, and provenance jump support."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.current_doc: Optional[pymupdf.Document] = None
        self.current_page_idx = 0
        self.zoom_factor = 1.25
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.clicked.connect(self.prev_page)
        toolbar.addWidget(self.btn_prev)

        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.valueChanged.connect(self.on_spin_changed)
        toolbar.addWidget(self.page_spin)

        self.page_total_lbl = QLabel("/ 0")
        self.page_total_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        toolbar.addWidget(self.page_total_lbl)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.clicked.connect(self.next_page)
        toolbar.addWidget(self.btn_next)

        toolbar.addStretch()

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedWidth(32)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        toolbar.addWidget(self.btn_zoom_out)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(32)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        toolbar.addWidget(self.btn_zoom_in)

        layout.addLayout(toolbar)

        # Scrollable image display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #263244; background: #0B1020; }")

        self.image_label = QLabel("No document loaded.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #64748B; font-size: 13px;")
        self.scroll_area.setWidget(self.image_label)

        layout.addWidget(self.scroll_area)

    def load_document(self, file_path: str, initial_page: int = 1):
        if self.current_doc:
            try:
                self.current_doc.close()
            except:
                pass

        p = Path(file_path).resolve()
        if not p.exists():
            self.image_label.setText(f"File not found: {p.name}")
            return

        try:
            self.current_doc = pymupdf.open(str(p))
            total_pages = len(self.current_doc)
            self.page_spin.setRange(1, max(1, total_pages))
            self.page_total_lbl.setText(f"/ {total_pages}")
            self.jump_to_page(initial_page)
        except Exception as e:
            self.image_label.setText(f"Failed to render PDF: {e}")

    def jump_to_page(self, page_number: int):
        if not self.current_doc or len(self.current_doc) == 0:
            return

        page_idx = max(0, min(page_number - 1, len(self.current_doc) - 1))
        self.current_page_idx = page_idx
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page_idx + 1)
        self.page_spin.blockSignals(False)

        self.render_current_page()
        self.page_changed.emit(page_idx + 1)

    def render_current_page(self):
        if not self.current_doc:
            return

        page = self.current_doc[self.current_page_idx]
        mat = pymupdf.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)

        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pixmap)
        self.image_label.adjustSize()

    def prev_page(self):
        if self.current_page_idx > 0:
            self.jump_to_page(self.current_page_idx)

    def next_page(self):
        if self.current_doc and self.current_page_idx < len(self.current_doc) - 1:
            self.jump_to_page(self.current_page_idx + 2)

    def on_spin_changed(self, val: int):
        self.jump_to_page(val)

    def zoom_in(self):
        self.zoom_factor = min(3.0, self.zoom_factor + 0.25)
        self.render_current_page()

    def zoom_out(self):
        self.zoom_factor = max(0.5, self.zoom_factor - 0.25)
        self.render_current_page()
