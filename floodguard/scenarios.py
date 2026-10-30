"""Scenario definitions and evaluation built on the core engineering functions."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd

from floodguard.hydraulics import (
    CapacityAssessment,
    HydraulicResult,
    assess_capacity,
    calculate_pipe_capacity,
)
from floodguard.runoff import RunoffResult, calculate_peak_runoff
from floodguard.validation import ValidationError

SCENARIO_COLUMNS = [
    "Scenario",
    "Catchment area (ha)",
    "Runoff coefficient",
    "Rainfall intensity (mm/h)",
    "Pipe diameter (m)",
    "Manning n",
    "Slope (%)",
    "Description",
]


@dataclass(frozen=True)
class Scenario:
    """A complete set of runoff and pipe inputs for one comparison case."""

    name: str
    catchment_area_ha: float
    runoff_coefficient: float
    rainfall_intensity_mm_h: float
    pipe_diameter_m: float
    manning_n: float
    slope_percent: float
    description: str = ""


@dataclass(frozen=True)
class ScenarioResult:
    """Runoff, capacity and utilisation results for a scenario."""

    scenario: Scenario
    runoff: RunoffResult
    hydraulics: HydraulicResult
    assessment: CapacityAssessment

    @property
    def name(self) -> str:
        return self.scenario.name

    @property
    def description(self) -> str:
        return self.scenario.description


DEFAULT_SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="Existing drainage configuration",
        catchment_area_ha=5.0,
        runoff_coefficient=0.75,
        rainfall_intensity_mm_h=90.0,
        pipe_diameter_m=1.0,
        manning_n=0.013,
        slope_percent=0.5,
        description="Illustrative baseline with a 1.0 m concrete pipe.",
    ),
    Scenario(
        name="Increased rainfall intensity",
        catchment_area_ha=5.0,
        runoff_coefficient=0.75,
        rainfall_intensity_mm_h=135.0,
        pipe_diameter_m=1.0,
        manning_n=0.013,
        slope_percent=0.5,
        description="Illustrative 50% intensity increase on the existing pipe.",
    ),
    Scenario(
        name="Upsized pipe diameter",
        catchment_area_ha=5.0,
        runoff_coefficient=0.75,
        rainfall_intensity_mm_h=90.0,
        pipe_diameter_m=1.2,
        manning_n=0.013,
        slope_percent=0.5,
        description="Illustrative capacity improvement from a 1.2 m pipe.",
    ),
)


def default_scenarios() -> tuple[Scenario, ...]:
    """Return the built-in demonstration scenarios."""
    return DEFAULT_SCENARIOS


def scenarios_to_dataframe(scenarios: Iterable[Scenario]) -> pd.DataFrame:
    """Convert scenarios into the editable table format used by the UI."""
    records = [
        {
            "Scenario": scenario.name,
            "Catchment area (ha)": scenario.catchment_area_ha,
            "Runoff coefficient": scenario.runoff_coefficient,
            "Rainfall intensity (mm/h)": scenario.rainfall_intensity_mm_h,
            "Pipe diameter (m)": scenario.pipe_diameter_m,
            "Manning n": scenario.manning_n,
            "Slope (%)": scenario.slope_percent,
            "Description": scenario.description,
        }
        for scenario in scenarios
    ]
    return pd.DataFrame(records, columns=SCENARIO_COLUMNS)


def default_scenarios_dataframe() -> pd.DataFrame:
    """Return the built-in scenarios as an editable dataframe."""
    return scenarios_to_dataframe(default_scenarios())


def _as_float(value: object, scenario_name: str, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"Scenario '{scenario_name}': {field_name} must be a numeric value."
        ) from exc


def dataframe_to_scenarios(dataframe: pd.DataFrame) -> list[Scenario]:
    """Validate an edited scenario table and return Scenario objects."""
    missing = [column for column in SCENARIO_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValidationError(
            f"Scenario table is missing columns: {', '.join(missing)}."
        )
    if dataframe.empty:
        raise ValidationError("At least one scenario is required.")

    scenarios: list[Scenario] = []
    for index, row in dataframe.iterrows():
        numeric_values = [
            row["Catchment area (ha)"],
            row["Runoff coefficient"],
            row["Rainfall intensity (mm/h)"],
            row["Pipe diameter (m)"],
            row["Manning n"],
            row["Slope (%)"],
        ]
        raw_name = row["Scenario"]
        name = "" if pd.isna(raw_name) else str(raw_name).strip()
        if not name and all(pd.isna(value) for value in numeric_values):
            continue
        if not name:
            raise ValidationError(f"Scenario row {index + 1} requires a name.")

        description = row.get("Description", "")
        description = "" if pd.isna(description) else str(description).strip()
        scenarios.append(
            Scenario(
                name=name,
                catchment_area_ha=_as_float(
                    row["Catchment area (ha)"], name, "catchment area"
                ),
                runoff_coefficient=_as_float(
                    row["Runoff coefficient"], name, "runoff coefficient"
                ),
                rainfall_intensity_mm_h=_as_float(
                    row["Rainfall intensity (mm/h)"], name, "rainfall intensity"
                ),
                pipe_diameter_m=_as_float(
                    row["Pipe diameter (m)"], name, "pipe diameter"
                ),
                manning_n=_as_float(row["Manning n"], name, "Manning n"),
                slope_percent=_as_float(row["Slope (%)"], name, "pipe slope"),
                description=description,
            )
        )

    if not scenarios:
        raise ValidationError("At least one scenario is required.")
    return scenarios


def evaluate_scenario(scenario: Scenario) -> ScenarioResult:
    """Calculate one scenario using the shared runoff and hydraulic functions."""
    runoff = calculate_peak_runoff(
        scenario.catchment_area_ha,
        scenario.rainfall_intensity_mm_h,
        scenario.runoff_coefficient,
    )
    hydraulics = calculate_pipe_capacity(
        scenario.pipe_diameter_m,
        scenario.manning_n,
        scenario.slope_percent,
    )
    assessment = assess_capacity(runoff.peak_runoff_m3_s, hydraulics.capacity_m3_s)
    return ScenarioResult(
        scenario=scenario,
        runoff=runoff,
        hydraulics=hydraulics,
        assessment=assessment,
    )


def evaluate_scenarios(scenarios: Sequence[Scenario]) -> list[ScenarioResult]:
    """Evaluate multiple scenarios in their given order."""
    return [evaluate_scenario(scenario) for scenario in scenarios]
