from __future__ import annotations
from pathlib import Path
from typing import List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
)


class DragDropZone(QFrame):
    """Interactive drag-and-drop document ingestion widget with file/folder pickers."""

    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame#Card {
                border: 1px dashed rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.02);
            }
            QFrame#Card:hover {
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(8)

        title_label = QLabel("Drop PDF documents here")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #EDEDED; letter-spacing: -0.2px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        sub_label = QLabel("Supports single documents, multi-page reports, or batch folders")
        sub_label.setStyleSheet("font-size: 12px; color: #8E8E93;")
        sub_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_files = QPushButton("Browse Files")
        self.btn_files.setObjectName("NavyButton")
        self.btn_files.clicked.connect(self.browse_files)
        btn_layout.addWidget(self.btn_files)

        self.btn_folder = QPushButton("Browse Folder")
        self.btn_folder.clicked.connect(self.browse_folder)
        btn_layout.addWidget(self.btn_folder)

        layout.addLayout(btn_layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame#Card { border: 2px dashed #D4AF37; background-color: #172033; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        files = []
        for url in event.mimeData().urls():
            local_path = Path(url.toLocalFile())
            if local_path.is_file() and local_path.suffix.lower() == ".pdf":
                files.append(str(local_path))
            elif local_path.is_dir():
                for p in local_path.glob("*.pdf"):
                    files.append(str(p))
                for p in local_path.glob("*.PDF"):
                    files.append(str(p))

        if files:
            self.files_selected.emit(sorted(list(set(files))))

    def browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Documents",
            "",
            "PDF Files (*.pdf *.PDF)"
        )
        if paths:
            self.files_selected.emit(paths)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing PDFs")
        if folder:
            f_path = Path(folder)
            files = [str(p) for p in f_path.glob("*.pdf")] + [str(p) for p in f_path.glob("*.PDF")]
            if files:
                self.files_selected.emit(sorted(files))
