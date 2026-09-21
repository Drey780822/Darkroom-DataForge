from datetime import datetime, timezone
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QLabel,
    QPushButton,
    QLineEdit,
)


class LogConsole(QFrame):
    """Real-time structured logging console with level coloring and filter search."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header bar
        header = QHBoxLayout()
        title = QLabel("PIPELINE LOGS")
        title.setObjectName("CardTitle")
        header.addWidget(title)

        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter logs...")
        self.search_input.setFixedWidth(150)
        header.addWidget(self.search_input)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_logs)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # Plain text display
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #070B16;
                color: #94A3B8;
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid #1E293B;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.log_text)

    def append_log(self, level: str, message: str):
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        color_map = {
            "INFO": "#94A3B8",
            "WARNING": "#F59E0B",
            "ERROR": "#EF4444",
            "DEBUG": "#64748B",
            "SUCCESS": "#22C55E",
        }
        color = color_map.get(level.upper(), "#94A3B8")
        html_line = f"<span style='color:#64748B;'>[{timestamp}]</span> <span style='color:{color}; font-weight:bold;'>[{level.upper()}]</span> <span style='color:#E2E8F0;'>{message}</span>"

        # Apply search filter if present
        filter_str = self.search_input.text().strip().lower()
        if filter_str and filter_str not in message.lower():
            return

        self.log_text.appendHtml(html_line)
        self.log_text.moveCursor(QTextCursor.End)

    def clear_logs(self):
        self.log_text.clear()
