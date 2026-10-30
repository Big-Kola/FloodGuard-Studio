"""Dashboard page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.hydraulics import APPROACHING, EXCEEDS
from floodguard.project import EngineeringProject
from gui.charts import UtilisationChart
from gui.theme import COLORS
from gui.widgets import (
    Banner,
    Card,
    GaugeWidget,
    MetricCard,
    StatusPill,
    alpha_color,
    clear_layout,
    hline,
    label,
)


class DashboardPage(QWidget):
    run_requested = Signal()
    save_requested = Signal()
    navigate_requested = Signal(str)
    example_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self._scope_visible = True
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(28, 22, 28, 28)
        self.layout.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label("Dashboard", "PageTitle"))
        titles.addWidget(
            label(
                "Preliminary drainage screening at a glance",
                "PageSubtitle",
            )
        )
        header.addLayout(titles)
        header.addStretch(1)
        self.example_button = QPushButton("Load Example")
        self.example_button.setObjectName("GhostButton")
        self.example_button.clicked.connect(self.example_requested)
        self.report_button = QPushButton("View Report")
        self.report_button.clicked.connect(
            lambda: self.navigate_requested.emit("reports")
        )
        self.run_button = QPushButton("Run Analysis")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.clicked.connect(self.run_requested)
        header.addWidget(self.example_button)
        header.addWidget(self.report_button)
        header.addWidget(self.run_button)
        self.layout.addLayout(header)

        self.hero = QFrame()
        self.hero.setObjectName("HeroCard")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_left = QVBoxLayout()
        hero_left.setSpacing(5)
        self.hero_eyebrow = label("CURRENT PROJECT", "CardTitle")
        hero_left.addWidget(self.hero_eyebrow)
        self.project_name = label("No project", "PageTitle", wrap=True)
        hero_left.addWidget(self.project_name)
        self.project_meta = label("", "Muted", wrap=True)
        hero_left.addWidget(self.project_meta)
        self.project_description = label("", "Faint", wrap=True)
        hero_left.addWidget(self.project_description)
        hero_layout.addLayout(hero_left, 1)
        hero_right = QVBoxLayout()
        hero_right.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.status_pill = StatusPill("NO DATA")
        hero_right.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignRight)
        actions = QHBoxLayout()
        self.open_network = QPushButton("Open Network")
        self.open_network.clicked.connect(
            lambda: self.navigate_requested.emit("network")
        )
        self.save_button = QPushButton("Save Project")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_requested)
        actions.addWidget(self.open_network)
        actions.addWidget(self.save_button)
        hero_right.addLayout(actions)
        hero_layout.addLayout(hero_right)
        self.layout.addWidget(self.hero)

        kpis = QHBoxLayout()
        kpis.setSpacing(12)
        self.runoff_metric = MetricCard("Peak runoff", "-", "m³/s", COLORS["accent"])
        self.capacity_metric = MetricCard(
            "Selected capacity", "-", "m³/s", COLORS["info"]
        )
        self.utilisation_metric = MetricCard("Utilisation", "-", "%", COLORS["success"])
        self.network_metric = MetricCard(
            "Network assets", "0", "pipes", COLORS["text_muted"]
        )
        for card in (
            self.runoff_metric,
            self.capacity_metric,
            self.utilisation_metric,
            self.network_metric,
        ):
            kpis.addWidget(card)
        self.layout.addLayout(kpis)

        middle = QHBoxLayout()
        middle.setSpacing(12)
        chart_card = Card("Pipe capacity utilisation")
        self.chart = UtilisationChart()
        chart_card.add(self.chart)
        chart_note = label(
            "Independent full-flow screening. Dashed bands are illustrative at 80% and 100%.",
            "Faint",
            wrap=True,
        )
        chart_card.add(chart_note)
        middle.addWidget(chart_card, 2)

        selected_card = Card("Selected pipe")
        selected_card.layout.setSpacing(6)
        self.selected_pipe = label("No pipe selected", "SectionTitle", wrap=True)
        self.selected_nodes = label("", "Muted", wrap=True)
        selected_card.add(self.selected_pipe)
        selected_card.add(self.selected_nodes)
        self.gauge = GaugeWidget()
        self.gauge.setFixedHeight(160)
        selected_card.add(self.gauge)
        self.selected_capacity = label("", "Muted", wrap=True)
        self.selected_footnote = label("", "Faint", wrap=True)
        selected_card.add(self.selected_capacity)
        selected_card.add(self.selected_footnote)
        selected_card.add(hline())
        self.understanding = label(
            "Utilisation compares the current project peak runoff with the selected "
            "pipe's independent full-flow capacity.",
            "Faint",
            wrap=True,
        )
        selected_card.add(self.understanding)
        middle.addWidget(selected_card, 1)
        self.layout.addLayout(middle)

        lower = QHBoxLayout()
        lower.setSpacing(12)
        warnings_card = Card("Screening flags")
        self.warnings_layout = QVBoxLayout()
        self.warnings_layout.setSpacing(7)
        warnings_card.add(self.warnings_layout)
        lower.addWidget(warnings_card, 3)

        project_card = Card("Project details")
        self.details_layout = QGridLayout()
        self.details_layout.setHorizontalSpacing(12)
        self.details_layout.setVerticalSpacing(7)
        project_card.add(self.details_layout)
        lower.addWidget(project_card, 2)
        self.layout.addLayout(lower)

        self.scope_banner = Banner(
            "Scope: this version screens each pipe independently. It does not route "
            "flows through the network or predict flood depths, extents or surcharge."
        )
        self.layout.addWidget(self.scope_banner)
        self.layout.addStretch(1)

    def set_scope_visible(self, visible: bool) -> None:
        self._scope_visible = visible
        self.scope_banner.setVisible(visible)

    def set_busy(self, busy: bool) -> None:
        self.run_button.setEnabled(not busy)
        self.run_button.setText("Analysing..." if busy else "Run Analysis")

    def set_project(self, project: EngineeringProject) -> None:
        self.project = project
        metadata = project.metadata
        self.project_name.setText(metadata.name)
        bits = [metadata.location, metadata.engineer]
        bits = [item for item in bits if item]
        self.project_meta.setText(
            "  |  ".join(bits) if bits else "No location or engineer recorded"
        )
        self.project_description.setText(
            metadata.description or "No project description"
        )
        self.project_description.setVisible(bool(metadata.description))
        self.network_metric.set_value(
            str(len(project.pipes)), "pipes", f"{len(project.nodes)} nodes"
        )
        self._fill_details(project)

    def _fill_details(self, project: EngineeringProject) -> None:
        clear_layout(self.details_layout)
        try:
            modified = datetime.fromisoformat(project.metadata.modified_at)
            modified_text = modified.strftime("%d %b %Y, %H:%M")
        except ValueError:
            modified_text = project.metadata.modified_at
        rows = [
            ("Project number", project.metadata.project_number or "Not specified"),
            ("Client", project.metadata.client or "Not specified"),
            ("Location", project.metadata.location or "Not specified"),
            ("Last modified", modified_text),
            ("Catchment", f"{project.catchment.area_ha:,.2f} ha"),
            (
                "Design rainfall",
                f"{project.catchment.rainfall_intensity_mm_h:,.1f} mm/h",
            ),
        ]
        for row, (key, value) in enumerate(rows):
            self.details_layout.addWidget(label(key, "Faint"), row, 0)
            self.details_layout.addWidget(label(value, "Muted", wrap=True), row, 1)
        self.details_layout.setColumnStretch(1, 1)

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        self.runoff_metric.set_value(
            f"{analysis.runoff.peak_runoff_m3_s:,.4f}",
            "m³/s",
            f"{analysis.runoff.peak_runoff_l_s:,.1f} L/s",
        )
        selected = analysis.selected_pipe
        if selected is None:
            self.capacity_metric.set_value("-", "m³/s", "no pipe")
            self.utilisation_metric.set_value("-", "%", "no pipe")
            self.gauge.set_utilisation(0, "No pipe selected")
            self.selected_pipe.setText("No pipe selected")
            self.selected_nodes.setText("Add a pipe on the Drainage Network page.")
            self.selected_capacity.setText("")
            self.selected_footnote.setText("")
            self.status_pill.setText("NO NETWORK DATA")
            self.status_pill.setStyleSheet(
                f"background: {COLORS['surface_raised']}; color: {COLORS['text_muted']};"
                f"border: 1px solid {COLORS['border']}; border-radius: 10px;"
                "padding: 4px 10px; font-size: 9px; font-weight: 700;"
            )
        else:
            assessment = selected.assessment
            self.capacity_metric.set_value(
                f"{selected.hydraulics.capacity_m3_s:,.4f}",
                "m³/s",
                selected.pipe.name,
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
            self.gauge.set_utilisation(
                assessment.utilisation_percent, assessment.classification
            )
            self.selected_pipe.setText(selected.pipe.name)
            self.selected_nodes.setText(
                f"{selected.pipe.from_node_id}  →  {selected.pipe.to_node_id}"
            )
            self.selected_capacity.setText(
                f"Capacity {selected.hydraulics.capacity_m3_s:,.4f} m³/s  |  "
                f"Velocity {selected.hydraulics.full_flow_velocity_m_s:,.2f} m/s"
            )
            self.selected_footnote.setText(
                f"D = {selected.pipe.diameter_m:,.2f} m  |  "
                f"S = {selected.pipe.slope_percent:,.2f}%  |  "
                f"n = {selected.pipe.manning_n:,.3f}"
            )
            self._set_status_from_analysis(analysis)

        labels = [item.pipe.id for item in analysis.pipes]
        values = [item.assessment.utilisation_percent for item in analysis.pipes]
        classes = [item.assessment.classification for item in analysis.pipes]
        self.chart.set_data(labels, values, classes)
        self._fill_warnings(analysis)

    def _set_status_from_analysis(self, analysis: ProjectAnalysis) -> None:
        classifications = [item.assessment.classification for item in analysis.pipes]
        if any(item == EXCEEDS for item in classifications):
            text, color = "ATTENTION REQUIRED", COLORS["danger"]
        elif any(item == APPROACHING for item in classifications):
            text, color = "REVIEW RECOMMENDED", COLORS["warning"]
        elif classifications:
            text, color = "SCREENING COMPLETE", COLORS["success"]
        else:
            text, color = "NO NETWORK DATA", COLORS["text_muted"]
        self.status_pill.setText(text)
        self.status_pill.setStyleSheet(
            f"background: {alpha_color(color, '22')}; color: {color};"
            f"border: 1px solid {alpha_color(color, '66')};"
            f"border-radius: 10px; padding: 4px 10px; font-size: 9px; font-weight: 700;"
        )

    def _fill_warnings(self, analysis: ProjectAnalysis) -> None:
        clear_layout(self.warnings_layout)
        visible = [item for item in analysis.warnings if item.level != "info"][:4]
        if not visible:
            good = label(
                "No capacity screening flags for the current inputs.",
                "SuccessText",
                wrap=True,
            )
            self.warnings_layout.addWidget(good)
        else:
            for warning in visible:
                color = (
                    COLORS["danger"]
                    if warning.level == "critical"
                    else COLORS["warning"]
                )
                text = QLabel(warning.message)
                text.setWordWrap(True)
                text.setStyleSheet(
                    f"color: {color}; font-size: 10px; line-height: 1.35;"
                )
                self.warnings_layout.addWidget(text)
        self.warnings_layout.addStretch(1)
        scope = label(analysis.scope_note, "Faint", wrap=True)
        self.warnings_layout.addWidget(scope)
