"""Single-pipe hydraulic screening page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import PipeAnalysis, ProjectAnalysis
from floodguard.hydraulics import APPROACHING, EXCEEDS
from floodguard.project import EngineeringProject
from gui.theme import COLORS
from gui.widgets import (
    Banner,
    Card,
    GaugeWidget,
    MetricCard,
    StatusPill,
    clear_layout,
    hline,
    label,
    mono,
)


class HydraulicsPage(QWidget):
    pipe_selected = Signal(str)
    navigate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self._current_id = ""
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

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label("Hydraulic Analysis", "PageTitle"))
        self.subtitle = label(
            "Independent full-flow pipe capacity screening",
            "PageSubtitle",
        )
        titles.addWidget(self.subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        self.pipe_combo = QComboBox()
        self.pipe_combo.setMinimumWidth(260)
        self.pipe_combo.currentIndexChanged.connect(self._combo_changed)
        header.addWidget(label("Pipe", "Muted"))
        header.addWidget(self.pipe_combo)
        self.network_button = QPushButton("Edit in Network")
        self.network_button.clicked.connect(
            lambda: self.navigate_requested.emit("network")
        )
        header.addWidget(self.network_button)
        layout.addLayout(header)

        self.scope = Banner(
            "This is an independent pipe screen using project-wide peak runoff. "
            "Upstream routing, part-full flow, surcharge, backwater and inlet/outlet "
            "losses are not modelled."
        )
        layout.addWidget(self.scope)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.runoff_metric = MetricCard("Peak runoff", "-", "m³/s", COLORS["accent"])
        self.capacity_metric = MetricCard(
            "Full-flow capacity", "-", "m³/s", COLORS["info"]
        )
        self.utilisation_metric = MetricCard("Utilisation", "-", "%", COLORS["success"])
        self.velocity_metric = MetricCard(
            "Full-flow velocity", "-", "m/s", COLORS["text_muted"]
        )
        for card in (
            self.runoff_metric,
            self.capacity_metric,
            self.utilisation_metric,
            self.velocity_metric,
        ):
            kpis.addWidget(card)
        layout.addLayout(kpis)

        middle = QHBoxLayout()
        middle.setSpacing(12)
        selected_card = Card("Selected pipe")
        selected_header = QHBoxLayout()
        selected_titles = QVBoxLayout()
        self.pipe_name = label("No pipe selected", "SectionTitle", wrap=True)
        self.pipe_route = label("", "Muted")
        selected_titles.addWidget(self.pipe_name)
        selected_titles.addWidget(self.pipe_route)
        selected_header.addLayout(selected_titles)
        selected_header.addStretch(1)
        self.status = StatusPill("NO DATA")
        selected_header.addWidget(self.status)
        selected_card.add(selected_header)
        self.gauge = GaugeWidget()
        selected_card.add(self.gauge)
        selected_card.add(hline())
        self.pipe_details = QGridLayout()
        self.pipe_details.setHorizontalSpacing(12)
        self.pipe_details.setVerticalSpacing(7)
        selected_card.add(self.pipe_details)
        middle.addWidget(selected_card, 2)

        calculation_card = Card("Calculation detail")
        calculation_card.add(label("MANNING FULL-FLOW EQUATION", "CardTitle"))
        calculation_card.add(mono("Q = (1/n) × A × R^(2/3) × S^(1/2)"))
        self.calculation_grid = QGridLayout()
        self.calculation_grid.setHorizontalSpacing(14)
        self.calculation_grid.setVerticalSpacing(7)
        calculation_card.add(self.calculation_grid)
        calculation_card.add(hline())
        self.substitution = label("", "Faint", wrap=True)
        calculation_card.add(self.substitution)
        calculation_card.add(
            label(
                "The pipe slope is assumed to represent the hydraulic energy slope. "
                "Full circular section, steady uniform flow.",
                "Faint",
                wrap=True,
            )
        )
        middle.addWidget(calculation_card, 3)
        layout.addLayout(middle)

        self.warning = Banner("", warning=True)
        layout.addWidget(self.warning)
        self.warning.setVisible(False)
        layout.addStretch(1)

    def set_project(
        self,
        project: EngineeringProject,
        selected_pipe_id: str = "",
    ) -> None:
        self.project = project
        self.pipe_combo.blockSignals(True)
        self.pipe_combo.clear()
        for pipe in project.pipes:
            self.pipe_combo.addItem(
                f"{pipe.name}  |  D {pipe.diameter_m:,.2f} m",
                pipe.id,
            )
        self.pipe_combo.blockSignals(False)
        target = selected_pipe_id or self._current_id
        if project.find_pipe(target) is None:
            target = project.pipes[0].id if project.pipes else ""
        self.set_selected_pipe(target)
        self.subtitle.setText(
            "Independent full-flow pipe capacity screening"
            + (f"  |  {project.metadata.name}" if project else "")
        )

    def set_scope_visible(self, visible: bool) -> None:
        self.scope.setVisible(visible)

    def set_selected_pipe(self, pipe_id: str) -> None:
        self._current_id = pipe_id
        index = self.pipe_combo.findData(pipe_id)
        if index >= 0:
            self.pipe_combo.blockSignals(True)
            self.pipe_combo.setCurrentIndex(index)
            self.pipe_combo.blockSignals(False)
        self._refresh()

    def _combo_changed(self, index: int) -> None:
        if index < 0:
            return
        pipe_id = self.pipe_combo.itemData(index)
        if not pipe_id:
            return
        self._current_id = pipe_id
        self.pipe_selected.emit(pipe_id)
        self._refresh()

    def _selected(self) -> PipeAnalysis | None:
        if self.analysis is None or not self._current_id:
            return None
        return self.analysis.pipe_result(self._current_id)

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        if self.analysis.selected_pipe is not None:
            fallback = self.analysis.selected_pipe.pipe.id
            if (
                not self._current_id
                or self.analysis.pipe_result(self._current_id) is None
            ):
                self._current_id = fallback
        self._refresh()

    def _refresh(self) -> None:
        clear_layout(self.pipe_details)
        clear_layout(self.calculation_grid)
        selected = self._selected()
        if self.analysis is not None:
            self.runoff_metric.set_value(
                f"{self.analysis.runoff.peak_runoff_m3_s:,.4f}",
                "m³/s",
                f"{self.analysis.runoff.peak_runoff_l_s:,.1f} L/s",
            )
        if selected is None:
            self.pipe_name.setText("No pipe selected")
            self.pipe_route.setText("Add or select a pipe to view screening results.")
            self.pipe_combo.setEnabled(bool(self.pipe_combo.count()))
            self.gauge.set_utilisation(0, "No pipe selected")
            self.status.setText("NO DATA")
            self.status.setStyleSheet(
                f"background: {COLORS['surface_raised']}; color: {COLORS['text_muted']};"
                f"border: 1px solid {COLORS['border']}; border-radius: 10px;"
                "padding: 4px 10px; font-size: 9px; font-weight: 700;"
            )
            self.capacity_metric.set_value("-", "m³/s", "no pipe")
            self.utilisation_metric.set_value("-", "%", "no pipe")
            self.velocity_metric.set_value("-", "m/s", "no pipe")
            self.warning.setVisible(False)
            return

        pipe = selected.pipe
        hydraulics = selected.hydraulics
        assessment = selected.assessment
        self.pipe_name.setText(pipe.name)
        self.pipe_route.setText(
            f"{pipe.from_node_id}  →  {pipe.to_node_id}  |  {pipe.material or 'material not specified'}"
        )
        self.status.set_classification(assessment.classification)
        self.gauge.set_utilisation(
            assessment.utilisation_percent, assessment.classification
        )
        self.capacity_metric.set_value(
            f"{hydraulics.capacity_m3_s:,.4f}", "m³/s", pipe.id
        )
        self.utilisation_metric.set_value(
            f"{assessment.utilisation_percent:,.1f}",
            "%",
            assessment.classification,
            accent=COLORS["success"]
            if assessment.classification not in (APPROACHING, EXCEEDS)
            else COLORS["warning"]
            if assessment.classification == APPROACHING
            else COLORS["danger"],
        )
        self.velocity_metric.set_value(
            f"{hydraulics.full_flow_velocity_m_s:,.3f}", "m/s", "at full flow"
        )

        rows = [
            ("Internal diameter", f"{pipe.diameter_m:,.3f} m"),
            ("Length", f"{pipe.length_m:,.2f} m"),
            ("Slope", f"{pipe.slope_percent:,.3f}%"),
            ("Manning n", f"{pipe.manning_n:,.4f}"),
            ("Material", pipe.material or "Not specified"),
        ]
        for row, (key, value) in enumerate(rows):
            self.pipe_details.addWidget(label(key, "Faint"), row, 0)
            self.pipe_details.addWidget(label(value, "Muted", wrap=True), row, 1)
        self.pipe_details.setColumnStretch(1, 1)

        calc_rows = [
            ("Cross-sectional area", f"{hydraulics.cross_section_area_m2:,.5f} m²"),
            ("Wetted perimeter", f"{hydraulics.wetted_perimeter_m:,.5f} m"),
            ("Hydraulic radius", f"{hydraulics.hydraulic_radius_m:,.5f} m"),
            ("Slope fraction", f"{hydraulics.slope_fraction:,.5f} m/m"),
            ("Capacity utilisation", f"{assessment.utilisation_percent:,.1f}%"),
            ("Classification", assessment.classification),
        ]
        for row, (key, value) in enumerate(calc_rows):
            self.calculation_grid.addWidget(label(key, "Faint"), row, 0)
            self.calculation_grid.addWidget(label(value, "Muted", wrap=True), row, 1)
        self.calculation_grid.setColumnStretch(1, 1)
        self.substitution.setText(
            f"Q = (1/{pipe.manning_n:.4f}) × {hydraulics.cross_section_area_m2:.5f} × "
            f"{hydraulics.hydraulic_radius_m:.5f}^(2/3) × "
            f"({hydraulics.slope_fraction:.5f})^(1/2) = {hydraulics.capacity_m3_s:.4f} m³/s"
        )

        if assessment.classification == EXCEEDS:
            self.warning.setText(
                "Project peak runoff exceeds this pipe's independent full-flow capacity. "
                "Flag for detailed hydraulic assessment; this screen does not predict flooding."
            )
            self.warning.setVisible(True)
        elif assessment.classification == APPROACHING:
            self.warning.setText(
                "Utilisation is in the illustrative 80-100% screening band. Review the "
                "design basis and verify with detailed hydraulic analysis."
            )
            self.warning.setVisible(True)
        else:
            self.warning.setVisible(False)
