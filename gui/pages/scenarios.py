"""Scenario comparison page."""

from __future__ import annotations

from dataclasses import replace
from typing import ClassVar

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.project import EngineeringProject
from floodguard.scenarios import Scenario
from gui.charts import UtilisationChart
from gui.dialogs import ScenarioDialog
from gui.theme import COLORS, STATUS_COLORS
from gui.widgets import Banner, Card, label


class ScenariosPage(QWidget):
    before_change = Signal()
    project_changed = Signal()
    status_message = Signal(str)
    scenario_selected = Signal(str)

    HEADERS: ClassVar[list[str]] = [
        "Scenario",
        "Area",
        "C",
        "Intensity",
        "D (m)",
        "Runoff",
        "Capacity",
        "Util.",
        "Status",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self.confirm_delete = True
        self._preferred_name = ""
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label("Scenario Comparison", "PageTitle"))
        self.subtitle = label(
            "Compare alternative rainfall, catchment and pipe assumptions",
            "PageSubtitle",
        )
        titles.addWidget(self.subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        self.add_button = QPushButton("Add Scenario")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self.add_scenario)
        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.clicked.connect(self.duplicate_scenario)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_scenario)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self.delete_scenario)
        for button in (
            self.add_button,
            self.duplicate_button,
            self.edit_button,
            self.delete_button,
        ):
            header.addWidget(button)
        layout.addLayout(header)

        self.scope_banner = Banner(
            "Scenarios are independent what-if calculations using the same simplified "
            "equations. They do not alter the current project and are not network simulations."
        )
        layout.addWidget(self.scope_banner)

        table_card = Card("Scenario results")
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.setMinimumHeight(185)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in range(1, len(self.HEADERS)):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.doubleClicked.connect(lambda _: self.edit_scenario())
        table_card.add(self.table)
        table_card.layout.setStretch(1, 1)
        layout.addWidget(table_card, 3)

        chart_card = Card("Scenario utilisation comparison")
        self.chart = UtilisationChart()
        self.chart.setMinimumHeight(245)
        chart_card.add(self.chart)
        chart_card.add(
            label(
                "Reference lines at 80% and 100% are illustrative screening bands.",
                "Faint",
                wrap=True,
            )
        )
        layout.addWidget(chart_card, 2)

        note = label(
            "Pipes may be compared at different diameters; each scenario calculates its "
            "own peak runoff and full-flow capacity from the values shown.",
            "Faint",
            wrap=True,
        )
        layout.addWidget(note)

    def set_project(self, project: EngineeringProject) -> None:
        self.project = project
        self.subtitle.setText(
            "Compare alternative rainfall, catchment and pipe assumptions"
            + (f"  |  {project.metadata.name}" if project else "")
        )

    def set_confirm_delete(self, enabled: bool) -> None:
        self.confirm_delete = enabled

    def set_scope_visible(self, visible: bool) -> None:
        self.scope_banner.setVisible(visible)

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        selected_row = self.table.currentRow()
        target_name = self._preferred_name
        if not target_name:
            selected = self.selected_scenario()
            target_name = selected.name if selected is not None else ""
        self.table.blockSignals(True)
        self.table.setRowCount(len(analysis.scenario_results))
        selected_row = next(
            (
                row
                for row, result in enumerate(analysis.scenario_results)
                if result.name == target_name
            ),
            selected_row,
        )
        for row, result in enumerate(analysis.scenario_results):
            item = result.scenario
            status_short = {
                "Within calculated capacity": "Within",
                "Approaching calculated capacity": "Approaching",
                "Calculated demand exceeds capacity": "Exceeds",
            }.get(result.assessment.classification, result.assessment.classification)
            values = [
                result.name,
                f"{result.scenario.catchment_area_ha:,.2f} ha",
                f"{result.scenario.runoff_coefficient:,.2f}",
                f"{result.scenario.rainfall_intensity_mm_h:,.0f} mm/h",
                f"{result.scenario.pipe_diameter_m:,.2f}",
                f"{result.runoff.peak_runoff_m3_s:,.3f}",
                f"{result.hydraulics.capacity_m3_s:,.3f}",
                f"{result.assessment.utilisation_percent:,.1f}%",
                status_short,
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column > 0:
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if column == len(values) - 1:
                    cell.setForeground(
                        QColor(
                            STATUS_COLORS.get(
                                result.assessment.classification,
                                COLORS["text_muted"],
                            )
                        )
                    )
                    cell.setToolTip(result.assessment.classification)
                cell.setData(Qt.ItemDataRole.UserRole, item.name)
                self.table.setItem(row, column, cell)
        if 0 <= selected_row < self.table.rowCount():
            self.table.selectRow(selected_row)
        elif self.table.rowCount():
            self.table.selectRow(0)
        self.table.blockSignals(False)
        selected = self.selected_scenario()
        self._preferred_name = selected.name if selected is not None else ""
        if selected is None:
            self.table.clearSelection()

        labels = [result.name for result in analysis.scenario_results]
        values = [
            result.assessment.utilisation_percent
            for result in analysis.scenario_results
        ]
        classes = [
            result.assessment.classification for result in analysis.scenario_results
        ]
        self.chart.set_data(
            labels,
            values,
            classes,
            empty_message="No scenarios defined",
        )
        self._update_button_state()

    def selected_scenario(self) -> Scenario | None:
        if self.project is None:
            return None
        row = self.table.currentRow()
        if row < 0 or row >= len(self.project.scenarios):
            return None
        return self.project.scenarios[row]

    def _selection_changed(self) -> None:
        scenario = self.selected_scenario()
        self._preferred_name = scenario.name if scenario is not None else ""
        self._update_button_state()
        if scenario is not None:
            self.scenario_selected.emit(scenario.name)

    def _update_button_state(self) -> None:
        has_selection = self.selected_scenario() is not None
        self.edit_button.setEnabled(has_selection)
        self.duplicate_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _defaults(self) -> Scenario:
        project = self.project
        assert project is not None
        pipe = project.pipes[0] if project.pipes else None
        return Scenario(
            name="",
            catchment_area_ha=project.catchment.area_ha,
            runoff_coefficient=project.catchment.runoff_coefficient,
            rainfall_intensity_mm_h=project.catchment.rainfall_intensity_mm_h,
            pipe_diameter_m=pipe.diameter_m if pipe else 1.0,
            manning_n=pipe.manning_n if pipe else 0.013,
            slope_percent=pipe.slope_percent if pipe else 0.5,
        )

    def _names(self) -> set[str]:
        return (
            {scenario.name for scenario in self.project.scenarios}
            if self.project
            else set()
        )

    def add_scenario(self) -> None:
        if self.project is None:
            return
        dialog = ScenarioDialog(
            parent=self,
            existing_names=self._names(),
            defaults=self._defaults(),
        )
        if dialog.exec() != ScenarioDialog.DialogCode.Accepted:
            return
        scenario = dialog.scenario()
        self.before_change.emit()
        self.project.scenarios.append(scenario)
        self._preferred_name = scenario.name
        self.project_changed.emit()
        self.status_message.emit(f"Added scenario '{scenario.name}'.")

    def duplicate_scenario(self) -> None:
        scenario = self.selected_scenario()
        if scenario is None or self.project is None:
            return
        existing = self._names()
        index = 2
        new_name = f"{scenario.name} (copy)"
        while new_name in existing:
            new_name = f"{scenario.name} (copy {index})"
            index += 1
        copy = replace(scenario, name=new_name)
        self.before_change.emit()
        self.project.scenarios.append(copy)
        self._preferred_name = copy.name
        self.project_changed.emit()
        self.status_message.emit(f"Duplicated scenario as '{new_name}'.")

    def edit_scenario(self) -> None:
        scenario = self.selected_scenario()
        if scenario is None or self.project is None:
            return
        row = self.project.scenarios.index(scenario)
        dialog = ScenarioDialog(
            scenario,
            parent=self,
            existing_names=self._names(),
        )
        if dialog.exec() != ScenarioDialog.DialogCode.Accepted:
            return
        updated = dialog.scenario()
        self.before_change.emit()
        self.project.scenarios[row] = updated
        self._preferred_name = updated.name
        self.project_changed.emit()
        self.status_message.emit(f"Updated scenario '{updated.name}'.")

    def delete_scenario(self) -> None:
        scenario = self.selected_scenario()
        if scenario is None or self.project is None:
            return
        if self.confirm_delete:
            answer = QMessageBox.question(
                self,
                "Delete scenario",
                f"Delete scenario '{scenario.name}'?",
                QMessageBox.StandardButton.Delete | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Delete:
                return
        self.before_change.emit()
        row = self.project.scenarios.index(scenario)
        self.project.scenarios.remove(scenario)
        remaining = self.project.scenarios
        self._preferred_name = (
            remaining[min(row, len(remaining) - 1)].name if remaining else ""
        )
        self.project_changed.emit()
        self.status_message.emit(f"Deleted scenario '{scenario.name}'.")
