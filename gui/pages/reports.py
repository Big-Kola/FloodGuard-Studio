"""Engineering report export page."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.project import EngineeringProject
from floodguard.reporting import (
    build_pipe_results_csv,
    build_scenario_csv,
    build_studio_pdf_report,
)
from gui.widgets import Banner, Card, hline, label


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned[:70] or "FloodGuard_Studio_Project"


class ReportsPage(QWidget):
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self._default_directory = str(
            Path.home() / "Documents" / "FloodGuard Studio" / "Reports"
        )
        self.last_export: Path | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(label("Engineering Reports", "PageTitle"))
        self.subtitle = label(
            "Export the current project inputs and calculated screening outputs",
            "PageSubtitle",
        )
        layout.addWidget(self.subtitle)

        self.scope_banner = Banner(
            "Reports contain independent full-flow pipe screening results only. "
            "They are not network hydraulic simulations and do not certify flood safety."
        )
        layout.addWidget(self.scope_banner)

        top = QHBoxLayout()
        top.setSpacing(12)
        report_card = Card("Project screening PDF")
        report_card.add(
            label(
                "A project-level report including metadata, catchment inputs, network "
                "inventory, selected-pipe detail, pipe screening summary, scenarios, "
                "assumptions and limitations.",
                "Muted",
                wrap=True,
            )
        )
        report_card.add(hline())
        self.pdf_summary = label("", "Faint", wrap=True)
        report_card.add(self.pdf_summary)
        self.pdf_button = QPushButton("Export Project PDF")
        self.pdf_button.setObjectName("PrimaryButton")
        self.pdf_button.clicked.connect(self.export_pdf)
        report_card.add(self.pdf_button)
        report_card.add_stretch()
        top.addWidget(report_card, 3)

        data_card = Card("Supporting data")
        data_card.add(
            label(
                "Pipe results and scenario comparisons are exported as UTF-8 CSV for "
                "audit, spreadsheet review or reporting support.",
                "Muted",
                wrap=True,
            )
        )
        data_card.add(hline())
        self.pipe_csv_button = QPushButton("Export Pipe Results CSV")
        self.pipe_csv_button.clicked.connect(self.export_pipe_csv)
        self.scenario_csv_button = QPushButton("Export Scenario CSV")
        self.scenario_csv_button.clicked.connect(self.export_scenario_csv)
        self.open_folder_button = QPushButton("Open Reports Folder")
        self.open_folder_button.setObjectName("GhostButton")
        self.open_folder_button.clicked.connect(self._open_folder)
        data_card.add(self.pipe_csv_button)
        data_card.add(self.scenario_csv_button)
        data_card.add(self.open_folder_button)
        data_card.add_stretch()
        top.addWidget(data_card, 2)
        layout.addLayout(top)

        contents_card = Card("Report contents and limitations")
        sections = [
            (
                "1. Project information",
                "Metadata, client, location, author and modification details.",
            ),
            (
                "2. Scope and methodology",
                "Rational Method and Manning full-flow equations with explicit limitations.",
            ),
            (
                "3. Catchment and design rainfall",
                "Current inputs and calculated peak runoff.",
            ),
            ("4. Drainage network", "Node inventory and individual pipe properties."),
            (
                "5. Selected pipe",
                "Detailed independent full-flow screening of the selected pipe.",
            ),
            (
                "6. Pipe screening summary",
                "Capacity and utilisation for every pipe in the project.",
            ),
            ("7. Scenarios", "Current saved scenario comparison results."),
            (
                "8. Limitations and next steps",
                "Assumptions, exclusions and recommended engineering checks.",
            ),
        ]
        for title, text in sections:
            row = QHBoxLayout()
            row.setSpacing(14)
            title_label = label(title, "Muted")
            title_label.setFixedWidth(230)
            row.addWidget(title_label)
            row.addWidget(label(text, "Faint", wrap=True), 1)
            contents_card.add(row)
        layout.addWidget(contents_card)
        layout.addStretch(1)
        self._update_state()

    def set_default_directory(self, directory: str) -> None:
        self._default_directory = directory

    def set_scope_visible(self, visible: bool) -> None:
        self.scope_banner.setVisible(visible)

    def set_project(self, project: EngineeringProject) -> None:
        self.project = project
        self.subtitle.setText(
            "Export the current project inputs and calculated screening outputs"
            + (f"  |  {project.metadata.name}" if project else "")
        )
        self._update_state()

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        self._update_state()

    def _update_state(self) -> None:
        ready = self.project is not None and self.analysis is not None
        for button in (
            self.pdf_button,
            self.pipe_csv_button,
            self.scenario_csv_button,
        ):
            button.setEnabled(ready)
        if not ready:
            self.pdf_summary.setText("Open a project and run the analysis first.")
            return
        assert self.project is not None
        assert self.analysis is not None
        self.pdf_summary.setText(
            f"Project: {self.project.metadata.name}\n"
            f"Network: {len(self.project.nodes)} nodes, {len(self.project.pipes)} pipes\n"
            f"Scenarios: {len(self.project.scenarios)}  |  "
            f"Generated on export with current results."
        )

    def _base_path(self, extension: str) -> str:
        assert self.project is not None
        directory = Path(self._default_directory)
        filename = (
            f"{_safe_filename(self.project.metadata.name)}_"
            f"{datetime.now():%Y%m%d}{extension}"
        )
        return str(directory / filename)

    def _ask_path(self, title: str, extension: str, filter_text: str) -> str:
        directory = Path(self._default_directory).expanduser()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError:
            directory = Path.home()
        self._default_directory = str(directory)
        filename, _ = QFileDialog.getSaveFileName(
            self,
            title,
            self._base_path(extension),
            filter_text,
        )
        return filename

    def export_pdf(self) -> None:
        if self.project is None or self.analysis is None:
            return
        path = self._ask_path(
            "Export Project Screening Report",
            ".pdf",
            "PDF report (*.pdf)",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != ".pdf":
            destination = destination.with_suffix(".pdf")
        try:
            payload = build_studio_pdf_report(self.project, self.analysis)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            QMessageBox.critical(self, "Report export failed", str(error))
            self.status_message.emit(f"Report export failed: {error}")
            return
        self.last_export = destination
        self._default_directory = str(destination.parent)
        self.status_message.emit(f"Project report exported to {destination}.")
        QMessageBox.information(
            self,
            "Report exported",
            f"Project PDF saved to:\n{destination}",
        )

    def export_pipe_csv(self) -> None:
        if self.analysis is None:
            return
        path = self._ask_path(
            "Export Pipe Results",
            ".csv",
            "CSV file (*.csv)",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != ".csv":
            destination = destination.with_suffix(".csv")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(build_pipe_results_csv(self.analysis))
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            QMessageBox.critical(self, "CSV export failed", str(error))
            return
        self.last_export = destination
        self._default_directory = str(destination.parent)
        self.status_message.emit(f"Pipe results exported to {destination}.")
        QMessageBox.information(self, "Pipe CSV exported", f"Saved to:\n{destination}")

    def export_scenario_csv(self) -> None:
        if self.analysis is None:
            return
        path = self._ask_path(
            "Export Scenario Results",
            ".csv",
            "CSV file (*.csv)",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != ".csv":
            destination = destination.with_suffix(".csv")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(
                build_scenario_csv(list(self.analysis.scenario_results))
            )
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            QMessageBox.critical(self, "CSV export failed", str(error))
            return
        self.last_export = destination
        self._default_directory = str(destination.parent)
        self.status_message.emit(f"Scenario results exported to {destination}.")
        QMessageBox.information(
            self, "Scenario CSV exported", f"Saved to:\n{destination}"
        )

    def _open_folder(self) -> None:
        directory = Path(self._default_directory)
        directory.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))
