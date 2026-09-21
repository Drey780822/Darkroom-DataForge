#!/usr/bin/env python3
"""Darkroom DataForge - Wits–merSETA Darkroom

Structured Data Extraction, Validation & Dataset Generation Platform.
Desktop Application & CLI Entry Point.
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def run_gui():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from gui.main_window import MainWindow

    # High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    # app.setApplicationName("Darkroom DataForge")
    app.setOrganizationName("Wits–merSETA Darkroom")

    window = MainWindow(workspace_dir="./dataforge_workspace")
    window.show()

    sys.exit(app.exec())


def main():
    # If CLI arguments provided (e.g. process, inspect, export, validate, --cli)
    if len(sys.argv) > 1 and sys.argv[1] in ["inspect", "process", "validate", "export", "--cli", "-h", "--help"]:
        from cli.main import main as cli_main
        argv = sys.argv[1:]
        if argv and argv[0] == "--cli":
            argv = argv[1:]
        sys.exit(cli_main(argv))
    else:
        run_gui()


if __name__ == "__main__":
    main()
