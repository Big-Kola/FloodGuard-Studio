"""Project and scenario dialogs."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from floodguard.scenarios import Scenario, evaluate_scenario
from floodguard.validation import ValidationError
from gui.widgets import hline, label


class NewProjectDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        default_engineer: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New FloodGuard Studio Project")
        self.setMinimumWidth(530)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(label("Create a new project", "PageTitle"))
        layout.addWidget(
            label(
                "A starter junction-to-outfall reach will be created and can be edited.",
                "Muted",
                wrap=True,
            )
        )
        layout.addWidget(hline())

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Riverside Drainage Study")
        self.number = QLineEdit()
        self.number.setPlaceholderText("Optional")
        self.client = QLineEdit()
        self.client.setPlaceholderText("Optional")
        self.location = QLineEdit()
        self.location.setPlaceholderText("Optional")
        self.engineer = QLineEdit(default_engineer)
        self.engineer.setPlaceholderText("Optional")
        self.description = QPlainTextEdit()
        self.description.setFixedHeight(68)
        self.description.setPlaceholderText("Optional project notes")
        form.addRow(label("Project name *", "Muted"), self.name)
        form.addRow(label("Project number", "Muted"), self.number)
        form.addRow(label("Client", "Muted"), self.client)
        form.addRow(label("Location", "Muted"), self.location)
        form.addRow(label("Engineer", "Muted"), self.engineer)
        form.addRow(label("Description", "Muted"), self.description)
        layout.addLayout(form)

        self.error = label("", "DangerText", wrap=True)
        self.error.setVisible(False)
        layout.addWidget(self.error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Create Project")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName(
            "PrimaryButton"
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name.setFocus()

    def _accept(self) -> None:
        if not self.name.text().strip():
            self.error.setText("Enter a project name.")
            self.error.setVisible(True)
            self.name.setFocus()
            return
        self.accept()

    def values(self) -> dict[str, str]:
        return {
            "name": self.name.text().strip(),
            "project_number": self.number.text().strip(),
            "client": self.client.text().strip(),
            "location": self.location.text().strip(),
            "engineer": self.engineer.text().strip(),
            "description": self.description.toPlainText().strip(),
        }


class ScenarioDialog(QDialog):
    def __init__(
        self,
        scenario: Scenario | None = None,
        *,
        parent: QWidget | None = None,
        existing_names: set[str] | None = None,
        defaults: Scenario | None = None,
    ) -> None:
        super().__init__(parent)
        self._existing_names = {name.casefold() for name in (existing_names or set())}
        if scenario is not None:
            self._existing_names.discard(scenario.name.casefold())
        self.setWindowTitle("Edit Scenario" if scenario else "New Scenario")
        self.setMinimumWidth(540)
        self._original = scenario
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        layout.addWidget(
            label("Edit scenario" if scenario else "Create scenario", "PageTitle")
        )
        layout.addWidget(
            label(
                "Scenario inputs are independent what-if values and do not modify the "
                "current catchment or network asset fields.",
                "Muted",
                wrap=True,
            )
        )
        layout.addWidget(hline())

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(9)
        self.name = QLineEdit(scenario.name if scenario else "")
        self.name.setPlaceholderText("Scenario name")
        self.area = self._spin(0.01, 99999.0, 3, 0.5, " ha")
        self.coefficient = self._spin(0.05, 1.0, 3, 0.05, "")
        self.rainfall = self._spin(0.1, 1000.0, 1, 1.0, " mm/h")
        self.diameter = self._spin(0.05, 10.0, 3, 0.05, " m")
        self.manning = self._spin(0.005, 0.2, 4, 0.001, "")
        self.slope = self._spin(0.01, 100.0, 3, 0.05, " %")
        if scenario is not None:
            self.area.setValue(scenario.catchment_area_ha)
            self.coefficient.setValue(scenario.runoff_coefficient)
            self.rainfall.setValue(scenario.rainfall_intensity_mm_h)
            self.diameter.setValue(scenario.pipe_diameter_m)
            self.manning.setValue(scenario.manning_n)
            self.slope.setValue(scenario.slope_percent)
        elif defaults is not None:
            self.area.setValue(defaults.catchment_area_ha)
            self.coefficient.setValue(defaults.runoff_coefficient)
            self.rainfall.setValue(defaults.rainfall_intensity_mm_h)
            self.diameter.setValue(defaults.pipe_diameter_m)
            self.manning.setValue(defaults.manning_n)
            self.slope.setValue(defaults.slope_percent)
        else:
            self.area.setValue(5.0)
            self.coefficient.setValue(0.75)
            self.rainfall.setValue(90.0)
            self.diameter.setValue(1.0)
            self.manning.setValue(0.013)
            self.slope.setValue(0.5)
        self.description = QPlainTextEdit(scenario.description if scenario else "")
        self.description.setFixedHeight(60)
        form.addRow(label("Scenario name *", "Muted"), self.name)
        form.addRow(label("Catchment area", "Muted"), self.area)
        form.addRow(label("Runoff coefficient, C", "Muted"), self.coefficient)
        form.addRow(label("Rainfall intensity", "Muted"), self.rainfall)
        form.addRow(label("Pipe diameter", "Muted"), self.diameter)
        form.addRow(label("Manning n", "Muted"), self.manning)
        form.addRow(label("Pipe slope", "Muted"), self.slope)
        form.addRow(label("Description", "Muted"), self.description)
        layout.addLayout(form)

        self.preview = QLabel("")
        self.preview.setObjectName("Formula")
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        self.error = label("", "DangerText", wrap=True)
        self.error.setVisible(False)
        layout.addWidget(self.error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Save Scenario")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName(
            "PrimaryButton"
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for spin in (
            self.area,
            self.coefficient,
            self.rainfall,
            self.diameter,
            self.manning,
            self.slope,
        ):
            spin.valueChanged.connect(self._update_preview)
        self._update_preview()
        self.name.setFocus()

    @staticmethod
    def _spin(
        minimum: float,
        maximum: float,
        decimals: int,
        step: float,
        suffix: str,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        return spin

    def scenario(self) -> Scenario:
        return Scenario(
            name=self.name.text().strip(),
            catchment_area_ha=self.area.value(),
            runoff_coefficient=self.coefficient.value(),
            rainfall_intensity_mm_h=self.rainfall.value(),
            pipe_diameter_m=self.diameter.value(),
            manning_n=self.manning.value(),
            slope_percent=self.slope.value(),
            description=self.description.toPlainText().strip(),
        )

    def _update_preview(self) -> None:
        try:
            result = evaluate_scenario(self.scenario())
        except ValidationError as error:
            self.preview.setText(str(error))
            return
        self.preview.setText(
            f"Q = {result.runoff.peak_runoff_m3_s:.4f} m³/s   |   "
            f"Capacity = {result.hydraulics.capacity_m3_s:.4f} m³/s   |   "
            f"Utilisation = {result.assessment.utilisation_percent:.1f}%   |   "
            f"{result.assessment.classification}"
        )

    def _accept(self) -> None:
        scenario = self.scenario()
        if not scenario.name:
            self.error.setText("Enter a scenario name.")
            self.error.setVisible(True)
            self.name.setFocus()
            return
        if scenario.name.casefold() in self._existing_names:
            self.error.setText("Scenario names must be unique.")
            self.error.setVisible(True)
            self.name.setFocus()
            return
        try:
            evaluate_scenario(scenario)
        except ValidationError as error:
            self.error.setText(str(error))
            self.error.setVisible(True)
            return
        self.accept()
