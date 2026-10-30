"""Catchment and rainfall input page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.project import Catchment, EngineeringProject
from floodguard.validation import ValidationError
from gui.widgets import Banner, Card, clear_layout, hline, label, mono


class HydrologyPage(QWidget):
    before_change = Signal()
    project_changed = Signal()
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
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
        outer.addWidget(scroll)

        layout.addWidget(label("Rainfall & Hydrology", "PageTitle"))
        self.subtitle = label(
            "Design rainfall, catchment area and runoff coefficient",
            "PageSubtitle",
        )
        layout.addWidget(self.subtitle)

        top = QHBoxLayout()
        top.setSpacing(12)
        input_card = Card("Catchment inputs")
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(11)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.area = QDoubleSpinBox()
        self.area.setRange(0.01, 99999.0)
        self.area.setDecimals(3)
        self.area.setSingleStep(0.5)
        self.area.setSuffix(" ha")
        self.rainfall = QDoubleSpinBox()
        self.rainfall.setRange(0.1, 1000.0)
        self.rainfall.setDecimals(1)
        self.rainfall.setSingleStep(1.0)
        self.rainfall.setSuffix(" mm/h")
        self.coefficient = QDoubleSpinBox()
        self.coefficient.setRange(0.05, 1.0)
        self.coefficient.setDecimals(3)
        self.coefficient.setSingleStep(0.05)
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(72)
        self.notes.setPlaceholderText(
            "Optional assumptions, catchment description and data sources"
        )
        form.addRow(label("Catchment area", "Muted"), self.area)
        form.addRow(label("Design rainfall intensity", "Muted"), self.rainfall)
        form.addRow(label("Runoff coefficient, C", "Muted"), self.coefficient)
        form.addRow(label("Notes", "Muted"), self.notes)
        input_card.add(form)
        self.error_label = label("", "DangerText", wrap=True)
        self.error_label.setVisible(False)
        input_card.add(self.error_label)
        input_card.add(hline())
        buttons = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("GhostButton")
        self.reset_button.clicked.connect(self._reset)
        self.apply_button = QPushButton("Apply Catchment Changes")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self._apply)
        buttons.addWidget(self.reset_button)
        buttons.addStretch(1)
        buttons.addWidget(self.apply_button)
        input_card.add(buttons)
        top.addWidget(input_card, 3)

        output_card = Card("Calculated runoff")
        self.runoff_value = label("-", "KpiValue")
        self.runoff_unit = label("m³/s", "KpiUnit")
        value_row = QHBoxLayout()
        value_row.addWidget(self.runoff_value)
        value_row.addWidget(self.runoff_unit, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)
        output_card.add(value_row)
        self.runoff_litres = label("", "Muted")
        output_card.add(self.runoff_litres)
        output_card.add(hline())
        output_card.add(label("RATIONAL METHOD", "CardTitle"))
        output_card.add(mono("Q = (1 / 360) × C × I × A"))
        self.substitution = label("", "Faint", wrap=True)
        output_card.add(self.substitution)
        output_card.add_stretch()
        top.addWidget(output_card, 2)
        layout.addLayout(top)

        method = Card("Method reference")
        self.method_layout = QVBoxLayout()
        self.method_layout.setSpacing(8)
        method.add(self.method_layout)
        layout.addWidget(method)

        self.scope = Banner(
            "The Rational Method estimates peak runoff only. It does not produce a "
            "hydrograph, runoff volume, flood depth or time-varying flow."
        )
        layout.addWidget(self.scope)
        self.scope.setVisible(False)
        layout.addStretch(1)

    def set_scope_visible(self, visible: bool) -> None:
        self.scope.setVisible(visible)

    def set_project(self, project: EngineeringProject) -> None:
        self.project = project
        catchment = project.catchment
        self.area.blockSignals(True)
        self.rainfall.blockSignals(True)
        self.coefficient.blockSignals(True)
        self.area.setValue(catchment.area_ha)
        self.rainfall.setValue(catchment.rainfall_intensity_mm_h)
        self.coefficient.setValue(catchment.runoff_coefficient)
        self.notes.setPlainText(catchment.notes)
        self.area.blockSignals(False)
        self.rainfall.blockSignals(False)
        self.coefficient.blockSignals(False)
        self.error_label.setVisible(False)
        self.subtitle.setText(
            "Design rainfall, catchment area and runoff coefficient"
            + (f"  |  {project.metadata.name}" if project else "")
        )
        self._fill_method()

    def _fill_method(self) -> None:
        clear_layout(self.method_layout)
        statements = [
            (
                "Peak flow",
                (
                    "Q = (1/360) × C × I × A, where I is in mm/h and A is in hectares; "
                    "Q is returned in m³/s."
                ),
            ),
            (
                "Runoff coefficient",
                (
                    "The coefficient represents the fraction of rainfall converted to "
                    "peak runoff. It must reflect verified land use and surface conditions."
                ),
            ),
            (
                "Design rainfall",
                (
                    "The entered intensity must correspond to an explicitly selected "
                    "duration and return period from an appropriate local source."
                ),
            ),
        ]
        for title, text in statements:
            row = QVBoxLayout()
            row.setSpacing(2)
            row.addWidget(label(title, "Muted"))
            row.addWidget(label(text, "Faint", wrap=True))
            self.method_layout.addLayout(row)
        self.method_layout.addWidget(
            label(
                "Reference thresholds are not universal design standards. Professional "
                "judgement and local requirements govern acceptance.",
                "WarningText",
                wrap=True,
            )
        )

    def _reset(self) -> None:
        if self.project is not None:
            self.set_project(self.project)
            self.status_message.emit("Catchment inputs reset to saved project values.")

    def _apply(self) -> None:
        if self.project is None:
            return
        catchment = Catchment(
            area_ha=self.area.value(),
            rainfall_intensity_mm_h=self.rainfall.value(),
            runoff_coefficient=self.coefficient.value(),
            notes=self.notes.toPlainText().strip(),
        )
        try:
            catchment.validate()
        except ValidationError as error:
            self.error_label.setText(str(error))
            self.error_label.setVisible(True)
            return
        current = self.project.catchment
        if (
            catchment.area_ha == current.area_ha
            and catchment.rainfall_intensity_mm_h == current.rainfall_intensity_mm_h
            and catchment.runoff_coefficient == current.runoff_coefficient
            and catchment.notes == current.notes
        ):
            self.status_message.emit("No catchment changes to apply.")
            return
        self.before_change.emit()
        self.project.catchment = catchment
        self.error_label.setVisible(False)
        self.project_changed.emit()
        self.status_message.emit("Catchment inputs updated and analysis recalculated.")

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        runoff = analysis.runoff
        self.runoff_value.setText(f"{runoff.peak_runoff_m3_s:,.4f}")
        self.runoff_litres.setText(f"{runoff.peak_runoff_l_s:,.1f} L/s")
        self.substitution.setText(
            f"(1/360) × {runoff.runoff_coefficient:,.3f} × "
            f"{runoff.rainfall_intensity_mm_h:,.1f} × {runoff.catchment_area_ha:,.3f}"
        )
