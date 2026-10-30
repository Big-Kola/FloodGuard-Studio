"""Context-sensitive right-hand properties panel."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.hydraulics import APPROACHING, EXCEEDS
from floodguard.project import EngineeringProject, Node, Pipe
from floodguard.validation import ValidationError
from gui.theme import COLORS
from gui.widgets import Card, clear_layout, hline, label


class PropertiesPanel(QFrame):
    before_change = Signal()
    project_changed = Signal()
    delete_requested = Signal(str, str)
    navigate_requested = Signal(str)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self._page = "dashboard"
        self._selection_kind = ""
        self._selection_id = ""
        self._current_path: Path | None = None
        self._dirty = False
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 16, 10)
        header_layout.addWidget(label("PROPERTIES", "CardTitle"))
        header_layout.addStretch(1)
        self.context_badge = label("", "Faint")
        header_layout.addWidget(self.context_badge)
        layout.addWidget(header)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {COLORS['border_soft']};")
        layout.addWidget(divider)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        self.content = QVBoxLayout(content)
        self.content.setContentsMargins(16, 14, 16, 18)
        self.content.setSpacing(12)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def set_context(
        self,
        page: str,
        project: EngineeringProject | None,
        analysis: ProjectAnalysis | None,
        selection_kind: str = "",
        selection_id: str = "",
        *,
        current_path: Path | None = None,
        dirty: bool = False,
    ) -> None:
        self._page = page
        self.project = project
        self.analysis = analysis
        self._selection_kind = selection_kind
        self._selection_id = selection_id
        self._current_path = current_path
        self._dirty = dirty
        self._render()

    def _render(self) -> None:
        clear_layout(self.content)
        if self.project is None:
            self.context_badge.setText("NO PROJECT")
            self.content.addWidget(
                label(
                    "Open or create a project to view properties.", "Muted", wrap=True
                )
            )
            self.content.addStretch(1)
            return
        if self._page == "network":
            self.context_badge.setText("NETWORK")
            self._render_network()
        elif self._page == "hydrology":
            self.context_badge.setText("CATCHMENT")
            self._render_summary()
        elif self._page == "hydraulics":
            self.context_badge.setText("PIPE")
            self._render_pipe_summary()
        elif self._page == "scenarios":
            self.context_badge.setText("SCENARIO")
            self._render_scenario()
        elif self._page == "reports":
            self.context_badge.setText("REPORT")
            self._render_report_scope()
        elif self._page == "settings":
            self.context_badge.setText("LOCAL")
            self._render_settings_context()
        else:
            self.context_badge.setText("PROJECT")
            self._render_dashboard()
        self.content.addStretch(1)

    def _render_dashboard(self) -> None:
        assert self.project is not None
        self.content.addWidget(label("Project readiness", "SectionTitle"))
        self.content.addWidget(
            label(
                "A quick integrity view of the saved project inputs and scope.",
                "Muted",
                wrap=True,
            )
        )
        project = self.project
        saved = self._current_path is not None and not self._dirty
        if saved:
            save_detail = f"Saved: {self._current_path.name}"
        elif self._dirty:
            save_detail = "Unsaved changes"
        else:
            save_detail = "New unsaved project"
        checks = [
            ("Project metadata", bool(project.metadata.name), "Name recorded"),
            (
                "Network inventory",
                bool(project.nodes and project.pipes),
                f"{len(project.pipes)} pipes",
            ),
            (
                "Catchment inputs",
                project.catchment.area_ha > 0,
                f"{project.catchment.area_ha:,.2f} ha",
            ),
            ("Scenarios", bool(project.scenarios), f"{len(project.scenarios)} saved"),
            ("Saved to disk", saved, save_detail),
        ]
        for title, passed, detail in checks:
            card = Card()
            card.layout.setContentsMargins(11, 9, 11, 9)
            row = QHBoxLayout()
            row.addWidget(label(title, "Muted"))
            row.addStretch(1)
            state = label(
                "READY" if passed else "REVIEW",
                "SuccessText" if passed else "WarningText",
            )
            row.addWidget(state)
            card.add(row)
            card.add(label(detail, "Faint"))
            self.content.addWidget(card)
        self._scope_block()

    def _render_summary(self) -> None:
        assert self.project is not None
        project = self.project
        self.content.addWidget(label("Catchment reference", "SectionTitle"))
        self._rows(
            [
                ("Area", f"{project.catchment.area_ha:,.3f} ha"),
                (
                    "Design intensity",
                    f"{project.catchment.rainfall_intensity_mm_h:,.1f} mm/h",
                ),
                ("Runoff coefficient", f"{project.catchment.runoff_coefficient:,.3f}"),
            ]
        )
        if project.catchment.notes:
            self.content.addWidget(label(project.catchment.notes, "Faint", wrap=True))
        self.content.addWidget(hline())
        if self.analysis is not None:
            self.content.addWidget(label("Calculated runoff", "SectionTitle"))
            self._rows(
                [
                    (
                        "Peak runoff",
                        f"{self.analysis.runoff.peak_runoff_m3_s:,.4f} m³/s",
                    ),
                    ("Equivalent", f"{self.analysis.runoff.peak_runoff_l_s:,.1f} L/s"),
                ]
            )
        note = Card("Method note")
        note.add(
            label(
                "Rational Method peak runoff. Edit inputs in the main hydrology workspace.",
                "Faint",
                wrap=True,
            )
        )
        self.content.addWidget(note)

    def _render_pipe_summary(self) -> None:
        assert self.analysis is not None and self.project is not None
        selected = (
            self.analysis.pipe_result(self._selection_id) or self.analysis.selected_pipe
        )
        if selected is None:
            self.content.addWidget(label("No pipe selected", "SectionTitle"))
            self.content.addWidget(
                label("Select a pipe on the network page.", "Muted", wrap=True)
            )
            return
        pipe = selected.pipe
        self.content.addWidget(label(pipe.name, "SectionTitle", wrap=True))
        self.content.addWidget(
            label(f"{pipe.id}  |  {pipe.from_node_id} → {pipe.to_node_id}", "Faint")
        )
        self._rows(
            [
                ("Diameter", f"{pipe.diameter_m:,.3f} m"),
                ("Length", f"{pipe.length_m:,.2f} m"),
                ("Slope", f"{pipe.slope_percent:,.3f}%"),
                ("Manning n", f"{pipe.manning_n:,.4f}"),
                ("Capacity", f"{selected.hydraulics.capacity_m3_s:,.4f} m³/s"),
                ("Utilisation", f"{selected.assessment.utilisation_percent:,.1f}%"),
                ("Classification", selected.assessment.classification),
            ]
        )
        status_color = COLORS["success"]
        if selected.assessment.classification == APPROACHING:
            status_color = COLORS["warning"]
        elif selected.assessment.classification == EXCEEDS:
            status_color = COLORS["danger"]
        banner = Card("Screening status")
        status = label(selected.assessment.classification, "Muted")
        status.setStyleSheet(f"color: {status_color}; font-weight: 700;")
        banner.add(status)
        banner.add(
            label(
                "Independent full-flow screen. Not a routed network result.",
                "Faint",
                wrap=True,
            )
        )
        self.content.addWidget(banner)

    def _render_scenario(self) -> None:
        assert self.project is not None
        scenario = next(
            (
                item
                for item in self.project.scenarios
                if item.name == self._selection_id
            ),
            self.project.scenarios[0] if self.project.scenarios else None,
        )
        if scenario is None:
            self.content.addWidget(label("No scenarios", "SectionTitle"))
            return
        result = next(
            (
                item
                for item in (self.analysis.scenario_results if self.analysis else ())
                if item.name == scenario.name
            ),
            None,
        )
        self.content.addWidget(label(scenario.name, "SectionTitle", wrap=True))
        if scenario.description:
            self.content.addWidget(label(scenario.description, "Muted", wrap=True))
        self._rows(
            [
                ("Area", f"{scenario.catchment_area_ha:,.3f} ha"),
                ("Runoff coefficient", f"{scenario.runoff_coefficient:,.3f}"),
                ("Intensity", f"{scenario.rainfall_intensity_mm_h:,.1f} mm/h"),
                ("Pipe diameter", f"{scenario.pipe_diameter_m:,.3f} m"),
                ("Manning n", f"{scenario.manning_n:,.4f}"),
                ("Slope", f"{scenario.slope_percent:,.3f}%"),
            ]
        )
        if result is not None:
            self.content.addWidget(hline())
            self._rows(
                [
                    ("Peak runoff", f"{result.runoff.peak_runoff_m3_s:,.4f} m³/s"),
                    ("Capacity", f"{result.hydraulics.capacity_m3_s:,.4f} m³/s"),
                    ("Utilisation", f"{result.assessment.utilisation_percent:,.1f}%"),
                    ("Classification", result.assessment.classification),
                ]
            )
        note = Card("Scenario scope")
        note.add(
            label(
                "Scenario values are what-if inputs and do not change the live project.",
                "Faint",
                wrap=True,
            )
        )
        self.content.addWidget(note)

    def _render_report_scope(self) -> None:
        self.content.addWidget(label("Report scope", "SectionTitle"))
        self.content.addWidget(
            label(
                "The PDF records project metadata, catchment inputs, the network inventory, "
                "selected-pipe detail, all pipe screening results, scenarios, assumptions "
                "and limitations.",
                "Muted",
                wrap=True,
            )
        )
        self.content.addWidget(hline())
        bullets = [
            "Uses current saved inputs at export time.",
            "No network routing or flood mapping.",
            "Independent full-flow pipe calculations.",
            "CSV exports support audit and review.",
        ]
        for bullet in bullets:
            self.content.addWidget(label("•  " + bullet, "Faint", wrap=True))
        self._scope_block()

    def _render_settings_context(self) -> None:
        self.content.addWidget(label("Local desktop application", "SectionTitle"))
        self.content.addWidget(
            label(
                "Preferences, recent files and default directories are stored on this "
                "computer. No account or network connection is required.",
                "Muted",
                wrap=True,
            )
        )
        self.content.addWidget(hline())
        self.content.addWidget(
            label(
                "Changes to defaults affect new projects only. Existing project files "
                "retain their own engineering values.",
                "Faint",
                wrap=True,
            )
        )

    def _render_network(self) -> None:
        assert self.project is not None
        if self._selection_kind == "node" and self._selection_id:
            node = self.project.find_node(self._selection_id)
            if node is not None:
                self._node_form(node)
                return
        if self._selection_kind == "pipe" and self._selection_id:
            pipe = self.project.find_pipe(self._selection_id)
            if pipe is not None:
                self._pipe_form(pipe)
                return
        self.content.addWidget(label("Network summary", "SectionTitle"))
        self._rows(
            [
                ("Nodes", str(len(self.project.nodes))),
                ("Pipes", str(len(self.project.pipes))),
                (
                    "Junctions",
                    str(
                        sum(1 for item in self.project.nodes if item.kind == "junction")
                    ),
                ),
                (
                    "Outfalls",
                    str(
                        sum(1 for item in self.project.nodes if item.kind == "outfall")
                    ),
                ),
            ]
        )
        self.content.addWidget(hline())
        self.content.addWidget(
            label(
                "Select a node or pipe in the canvas to edit its properties. "
                "Schematic coordinates are for layout only and are not survey coordinates.",
                "Muted",
                wrap=True,
            )
        )
        self._scope_block()

    def _node_form(self, node: Node) -> None:
        self.content.addWidget(label("NODE", "Faint"))
        self.content.addWidget(label(node.name, "SectionTitle", wrap=True))
        self.content.addWidget(label(node.id, "Faint"))
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        name = QLineEdit(node.name)
        kind = QComboBox()
        kind.addItem("Junction", "junction")
        kind.addItem("Outfall", "outfall")
        kind.setCurrentIndex(0 if node.kind == "junction" else 1)
        x = self._spin(-100000, 100000, 1, node.x)
        y = self._spin(-100000, 100000, 1, node.y)
        invert = self._spin(-1000, 10000, 3, node.invert_elevation_m, " m")
        notes = QPlainTextEdit(node.notes)
        notes.setFixedHeight(58)
        notes.setPlaceholderText("Optional node notes")
        form.addRow(label("Name", "Faint"), name)
        form.addRow(label("Type", "Faint"), kind)
        form.addRow(label("Schematic X", "Faint"), x)
        form.addRow(label("Schematic Y", "Faint"), y)
        form.addRow(label("Invert", "Faint"), invert)
        form.addRow(label("Notes", "Faint"), notes)
        self.content.addLayout(form)
        self.content.addWidget(
            label(
                "Schematic X/Y control drawing position only. Invert elevation is stored "
                "as project data but is not used by the current screening equations.",
                "Faint",
                wrap=True,
            )
        )
        row = QHBoxLayout()
        delete = QPushButton("Delete")
        delete.setObjectName("DangerButton")
        delete.clicked.connect(lambda: self.delete_requested.emit("node", node.id))
        apply = QPushButton("Apply Changes")
        apply.setObjectName("PrimaryButton")
        apply.clicked.connect(
            lambda: self._apply_node(node, name, kind, x, y, invert, notes)
        )
        row.addWidget(delete)
        row.addStretch(1)
        row.addWidget(apply)
        self.content.addLayout(row)

    def _apply_node(
        self,
        node: Node,
        name: QLineEdit,
        kind: QComboBox,
        x: QDoubleSpinBox,
        y: QDoubleSpinBox,
        invert: QDoubleSpinBox,
        notes: QPlainTextEdit,
    ) -> None:
        if not name.text().strip():
            self.status_message.emit("Node name must not be empty.")
            return
        candidate = replace(
            node,
            name=name.text().strip(),
            kind=kind.currentData(),
            x=x.value(),
            y=y.value(),
            invert_elevation_m=invert.value(),
            notes=notes.toPlainText().strip(),
        )
        if candidate == node:
            self.status_message.emit("No node changes to apply.")
            return
        self.before_change.emit()
        node.name = candidate.name
        node.kind = candidate.kind
        node.x = candidate.x
        node.y = candidate.y
        node.invert_elevation_m = candidate.invert_elevation_m
        node.notes = candidate.notes
        self.project_changed.emit()
        self.status_message.emit(f"Updated node {node.name}.")

    def _pipe_form(self, pipe: Pipe) -> None:
        self.content.addWidget(label("PIPE", "Faint"))
        self.content.addWidget(label(pipe.name, "SectionTitle", wrap=True))
        self.content.addWidget(label(pipe.id, "Faint"))
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        name = QLineEdit(pipe.name)
        from_node = QComboBox()
        to_node = QComboBox()
        assert self.project is not None
        for node in self.project.nodes:
            from_node.addItem(f"{node.id} | {node.name}", node.id)
            to_node.addItem(f"{node.id} | {node.name}", node.id)
        from_node.setCurrentIndex(max(0, from_node.findData(pipe.from_node_id)))
        to_node.setCurrentIndex(max(0, to_node.findData(pipe.to_node_id)))
        diameter = self._spin(0.05, 10.0, 3, pipe.diameter_m, " m")
        length = self._spin(0.1, 100000.0, 2, pipe.length_m, " m")
        slope = self._spin(0.01, 100.0, 3, pipe.slope_percent, " %")
        manning = self._spin(0.005, 0.2, 4, pipe.manning_n)
        material = QComboBox()
        material.setEditable(True)
        material.addItems(
            ["Concrete", "PVC", "HDPE", "Clay", "Ductile iron", "Steel", "Other"]
        )
        if pipe.material:
            index = material.findText(pipe.material)
            if index >= 0:
                material.setCurrentIndex(index)
            else:
                material.setEditText(pipe.material)
        notes = QPlainTextEdit(pipe.notes)
        notes.setFixedHeight(58)
        notes.setPlaceholderText("Optional pipe notes")
        form.addRow(label("Name", "Faint"), name)
        form.addRow(label("From node", "Faint"), from_node)
        form.addRow(label("To node", "Faint"), to_node)
        form.addRow(label("Diameter", "Faint"), diameter)
        form.addRow(label("Length", "Faint"), length)
        form.addRow(label("Slope", "Faint"), slope)
        form.addRow(label("Manning n", "Faint"), manning)
        form.addRow(label("Material", "Faint"), material)
        form.addRow(label("Notes", "Faint"), notes)
        self.content.addLayout(form)
        if self.analysis is not None:
            result = self.analysis.pipe_result(pipe.id)
            if result is not None:
                self.content.addWidget(hline())
                self._rows(
                    [
                        ("Capacity", f"{result.hydraulics.capacity_m3_s:,.4f} m³/s"),
                        (
                            "Utilisation",
                            f"{result.assessment.utilisation_percent:,.1f}%",
                        ),
                        ("Classification", result.assessment.classification),
                    ]
                )
        row = QHBoxLayout()
        delete = QPushButton("Delete")
        delete.setObjectName("DangerButton")
        delete.clicked.connect(lambda: self.delete_requested.emit("pipe", pipe.id))
        apply = QPushButton("Apply Changes")
        apply.setObjectName("PrimaryButton")
        apply.clicked.connect(
            lambda: self._apply_pipe(
                pipe,
                name,
                from_node,
                to_node,
                diameter,
                length,
                slope,
                manning,
                material,
                notes,
            )
        )
        row.addWidget(delete)
        row.addStretch(1)
        row.addWidget(apply)
        self.content.addLayout(row)

    def _apply_pipe(
        self,
        pipe: Pipe,
        name: QLineEdit,
        from_node: QComboBox,
        to_node: QComboBox,
        diameter: QDoubleSpinBox,
        length: QDoubleSpinBox,
        slope: QDoubleSpinBox,
        manning: QDoubleSpinBox,
        material: QComboBox,
        notes: QPlainTextEdit,
    ) -> None:
        if not name.text().strip():
            self.status_message.emit("Pipe name must not be empty.")
            return
        if from_node.currentData() == to_node.currentData():
            self.status_message.emit("A pipe must connect two different nodes.")
            return
        candidate = replace(
            pipe,
            name=name.text().strip(),
            from_node_id=from_node.currentData(),
            to_node_id=to_node.currentData(),
            diameter_m=diameter.value(),
            length_m=length.value(),
            slope_percent=slope.value(),
            manning_n=manning.value(),
            material=material.currentText().strip(),
            notes=notes.toPlainText().strip(),
        )
        try:
            candidate.validate()
        except ValidationError as error:
            self.status_message.emit(str(error))
            return
        if candidate == pipe:
            self.status_message.emit("No pipe changes to apply.")
            return
        self.before_change.emit()
        for field in (
            "name",
            "from_node_id",
            "to_node_id",
            "diameter_m",
            "length_m",
            "slope_percent",
            "manning_n",
            "material",
            "notes",
        ):
            setattr(pipe, field, getattr(candidate, field))
        self.project_changed.emit()
        self.status_message.emit(f"Updated {pipe.name}.")

    def _rows(self, rows: list[tuple[str, str]]) -> None:
        grid = QFormLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(7)
        for key, value in rows:
            grid.addRow(label(key, "Faint"), label(value, "Muted", wrap=True))
        self.content.addLayout(grid)

    def _scope_block(self) -> None:
        scope = Card("Analysis scope")
        scope.add(
            label(
                "Independent full-flow pipe screening only. No network routing, flood "
                "depth, flood extent or structural assessment is produced.",
                "Faint",
                wrap=True,
            )
        )
        self.content.addWidget(scope)

    @staticmethod
    def _spin(
        minimum: float,
        maximum: float,
        decimals: int,
        value: float,
        suffix: str = "",
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setValue(value)
        if suffix:
            spin.setSuffix(suffix)
        return spin
