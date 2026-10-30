"""Render documentation screenshots with the offscreen Qt platform."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_OPENGL", "software")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="floodguard-shots-")

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.state import AppSettings
from gui.theme import apply_theme

PAGES = [
    ("01-dashboard.png", "dashboard"),
    ("02-network.png", "network"),
    ("03-hydrology.png", "hydrology"),
    ("04-hydraulics.png", "hydraulics"),
    ("05-scenarios.png", "scenarios"),
    ("06-reports.png", "reports"),
    ("07-settings.png", "settings"),
]


def settle(app: QApplication) -> None:
    for _ in range(4):
        app.processEvents()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FloodGuard Studio")
    apply_theme(app)
    settings = AppSettings(
        default_project_directory=str(
            Path.home() / "Documents" / "FloodGuard Studio" / "Projects"
        ),
        default_reports_directory=str(
            Path.home() / "Documents" / "FloodGuard Studio" / "Reports"
        ),
    )
    window = MainWindow(settings=settings)
    window.resize(1480, 930)
    window.show()
    settle(app)

    window.load_example()
    window._select_pipe("P-02")
    window.dirty = False
    window._update_project_labels()
    settle(app)

    destination = ROOT / "docs" / "screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    for filename, page in PAGES:
        window.navigate(page)
        settle(app)
        path = destination / filename
        if not window.grab().save(str(path), "PNG"):
            raise RuntimeError(f"Could not save screenshot: {path}")
        print(f"Saved {path.relative_to(ROOT)}")

    window.dirty = False
    window.close()
    settle(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
