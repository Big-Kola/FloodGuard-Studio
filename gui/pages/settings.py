"""Application settings page."""

from __future__ import annotations

from pathlib import Path

import PySide6
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from floodguard.project import APP_NAME, PROJECT_EXTENSION, SCHEMA_VERSION
from gui.state import AppSettings
from gui.widgets import Banner, Card, hline, label


class SettingsPage(QWidget):
    settings_changed = Signal(object)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = AppSettings()
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        layout.addWidget(label("Settings", "PageTitle"))
        layout.addWidget(
            label(
                "Local application preferences and new-project defaults",
                "PageSubtitle",
            )
        )

        directories = Card("File locations")
        directory_form = QFormLayout()
        directory_form.setHorizontalSpacing(18)
        directory_form.setVerticalSpacing(10)
        self.projects_dir = QLineEdit()
        self.reports_dir = QLineEdit()
        directory_form.addRow(
            label("Default project folder", "Muted"),
            self._directory_row(self.projects_dir),
        )
        directory_form.addRow(
            label("Default reports folder", "Muted"),
            self._directory_row(self.reports_dir),
        )
        directories.add(directory_form)
        layout.addWidget(directories)

        defaults = Card("New project defaults")
        default_form = QFormLayout()
        default_form.setHorizontalSpacing(18)
        default_form.setVerticalSpacing(10)
        self.area = QDoubleSpinBox()
        self.area.setRange(0.01, 99999.0)
        self.area.setDecimals(3)
        self.area.setSuffix(" ha")
        self.rainfall = QDoubleSpinBox()
        self.rainfall.setRange(0.1, 1000.0)
        self.rainfall.setDecimals(1)
        self.rainfall.setSuffix(" mm/h")
        self.coefficient = QDoubleSpinBox()
        self.coefficient.setRange(0.05, 1.0)
        self.coefficient.setDecimals(3)
        self.coefficient.setSingleStep(0.05)
        default_form.addRow(label("Catchment area", "Muted"), self.area)
        default_form.addRow(label("Design rainfall intensity", "Muted"), self.rainfall)
        default_form.addRow(label("Runoff coefficient", "Muted"), self.coefficient)
        defaults.add(default_form)
        defaults.add(
            label(
                "These values seed new projects only. Existing projects are never changed.",
                "Faint",
                wrap=True,
            )
        )
        layout.addWidget(defaults)

        behaviour = Card("Interface and safeguards")
        self.confirm_delete = QCheckBox(
            "Ask before deleting nodes, pipes and scenarios"
        )
        self.scope_notes = QCheckBox(
            "Show engineering scope reminders in the workspace"
        )
        behaviour.add(self.confirm_delete)
        behaviour.add(self.scope_notes)
        layout.addWidget(behaviour)

        software = Card("Application information")
        software.add(label(f"{APP_NAME}", "SectionTitle"))
        software.add(
            label(
                f"Project schema v{SCHEMA_VERSION}  |  Files: *{PROJECT_EXTENSION}\n"
                f"PySide6 {PySide6.__version__}  |  Offline desktop application",
                "Muted",
                wrap=True,
            )
        )
        software.add(hline())
        software.add(
            label(
                "All calculations and project files remain on this computer. "
                "The application does not use a cloud service, telemetry or an internal web server.",
                "Faint",
                wrap=True,
            )
        )
        layout.addWidget(software)

        layout.addWidget(
            Banner(
                "Defaults are stored locally. Engineering results are recalculated from "
                "project inputs and are never loaded from a remote service."
            )
        )
        layout.addStretch(1)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(28, 8, 28, 14)
        self.reset_button = QPushButton("Reset to Defaults")
        self.reset_button.setObjectName("GhostButton")
        self.reset_button.clicked.connect(self._reset)
        self.save_button = QPushButton("Save Settings")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self._save)
        footer_layout.addWidget(self.reset_button)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.save_button)
        outer.addWidget(footer)

    def _directory_row(self, field: QLineEdit) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(field, 1)
        button = QPushButton("Browse")
        button.setObjectName("GhostButton")
        button.clicked.connect(lambda: self._browse(field))
        row.addWidget(button)
        return container

    def _browse(self, field: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select folder",
            field.text().strip() or str(Path.home()),
        )
        if directory:
            field.setText(directory)

    def set_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.projects_dir.setText(settings.default_project_directory)
        self.reports_dir.setText(settings.default_reports_directory)
        self.area.setValue(settings.default_area_ha)
        self.rainfall.setValue(settings.default_rainfall_intensity_mm_h)
        self.coefficient.setValue(settings.default_runoff_coefficient)
        self.confirm_delete.setChecked(settings.confirm_delete)
        self.scope_notes.setChecked(settings.show_scope_notes)

    def _reset(self) -> None:
        self.set_settings(AppSettings())
        self.status_message.emit("Settings form reset to defaults. Save to persist.")

    def _save(self) -> None:
        project_directory = self.projects_dir.text().strip()
        reports_directory = self.reports_dir.text().strip()
        if not project_directory or not reports_directory:
            QMessageBox.warning(
                self,
                "Folder required",
                "Choose both a default project folder and a default reports folder.",
            )
            return
        settings = AppSettings(
            default_project_directory=project_directory,
            default_reports_directory=reports_directory,
            default_area_ha=self.area.value(),
            default_rainfall_intensity_mm_h=self.rainfall.value(),
            default_runoff_coefficient=self.coefficient.value(),
            confirm_delete=self.confirm_delete.isChecked(),
            show_scope_notes=self.scope_notes.isChecked(),
            recent_files=list(self.settings.recent_files),
        )
        try:
            for directory in (
                settings.default_project_directory,
                settings.default_reports_directory,
            ):
                Path(directory).expanduser().mkdir(parents=True, exist_ok=True)
            settings.save()
        except OSError as error:
            QMessageBox.critical(self, "Settings not saved", str(error))
            return
        self.settings = settings
        self.settings_changed.emit(settings)
        self.status_message.emit("Settings saved.")
        QMessageBox.information(self, "Settings saved", "Application settings updated.")
