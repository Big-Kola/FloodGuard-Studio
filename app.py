"""FloodGuard Studio desktop application entry point."""

from __future__ import annotations

import multiprocessing
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from floodguard import __version__
from gui.branding import app_icon
from gui.main_window import MainWindow
from gui.theme import apply_theme


def main() -> int:
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("FloodGuard Studio")
    app.setApplicationDisplayName("FloodGuard Studio")
    app.setOrganizationName("FloodGuard")
    app.setApplicationVersion(__version__)
    apply_theme(app)
    icon = app_icon()
    app.setWindowIcon(icon)
    window = MainWindow()
    window.set_window_icon(icon)
    window.show()
    window.raise_()
    window.activateWindow()
    QTimer.singleShot(150, window.repaint)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
