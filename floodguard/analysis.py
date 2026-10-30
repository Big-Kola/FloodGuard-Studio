"""Project-level screening analysis assembled from the validated core modules."""

from __future__ import annotations

from dataclasses import dataclass

from floodguard.hydraulics import (
    APPROACHING,
    EXCEEDS,
    CapacityAssessment,
    HydraulicResult,
    assess_capacity,
    calculate_pipe_capacity,
)
from floodguard.project import EngineeringProject, Pipe
from floodguard.runoff import RunoffResult, calculate_peak_runoff
from floodguard.scenarios import ScenarioResult, evaluate_scenario


@dataclass(frozen=True)
class PipeAnalysis:
    """Independent full-flow screening result for one pipe."""

    pipe: Pipe
    hydraulics: HydraulicResult
    assessment: CapacityAssessment


@dataclass(frozen=True)
class AnalysisWarning:
    level: str
    message: str


@dataclass(frozen=True)
class ProjectAnalysis:
    """Current project screening results, excluding network-wide simulation."""

    runoff: RunoffResult
    pipes: tuple[PipeAnalysis, ...]
    scenario_results: tuple[ScenarioResult, ...]
    selected_pipe: PipeAnalysis | None
    warnings: tuple[AnalysisWarning, ...]

    def pipe_result(self, pipe_id: str) -> PipeAnalysis | None:
        return next((item for item in self.pipes if item.pipe.id == pipe_id), None)

    @property
    def network_pipe_count(self) -> int:
        return len(self.pipes)

    @property
    def scope_note(self) -> str:
        return (
            "Pipe capacities are independent full-flow screening calculations. "
            "FloodGuard Studio does not currently perform network-wide hydraulic routing."
        )


def analyse_pipe(project: EngineeringProject, pipe: Pipe) -> PipeAnalysis:
    runoff = calculate_peak_runoff(
        project.catchment.area_ha,
        project.catchment.rainfall_intensity_mm_h,
        project.catchment.runoff_coefficient,
    )
    hydraulics = calculate_pipe_capacity(
        pipe.diameter_m,
        pipe.manning_n,
        pipe.slope_percent,
    )
    assessment = assess_capacity(runoff.peak_runoff_m3_s, hydraulics.capacity_m3_s)
    return PipeAnalysis(pipe=pipe, hydraulics=hydraulics, assessment=assessment)


def analyse_project(
    project: EngineeringProject,
    selected_pipe_id: str | None = None,
) -> ProjectAnalysis:
    """Analyse the current catchment and every pipe using the shared engine."""
    project.validate()
    runoff = calculate_peak_runoff(
        project.catchment.area_ha,
        project.catchment.rainfall_intensity_mm_h,
        project.catchment.runoff_coefficient,
    )
    pipe_results = tuple(analyse_pipe(project, pipe) for pipe in project.pipes)
    selected = next(
        (item for item in pipe_results if item.pipe.id == selected_pipe_id),
        pipe_results[0] if pipe_results else None,
    )
    scenario_results = tuple(evaluate_scenario(item) for item in project.scenarios)

    warnings: list[AnalysisWarning] = []
    for item in pipe_results:
        if item.assessment.classification == EXCEEDS:
            warnings.append(
                AnalysisWarning(
                    "critical",
                    (
                        f"{item.pipe.name}: estimated runoff exceeds calculated "
                        f"full-flow capacity ({item.assessment.utilisation_percent:.1f}%). "
                        "Flag for detailed hydraulic assessment."
                    ),
                )
            )
        elif item.assessment.classification == APPROACHING:
            warnings.append(
                AnalysisWarning(
                    "warning",
                    (
                        f"{item.pipe.name}: utilisation is "
                        f"{item.assessment.utilisation_percent:.1f}%, within the "
                        "illustrative 80-100% screening band."
                    ),
                )
            )
    if not pipe_results:
        warnings.append(
            AnalysisWarning(
                "info",
                "No drainage pipes are defined. Add a pipe on the Drainage Network page.",
            )
        )
    warnings.append(
        AnalysisWarning(
            "info",
            "Scope: Pipe capacities are independent full-flow screening calculations; "
            "network-wide hydraulic routing is not performed.",
        )
    )

    return ProjectAnalysis(
        runoff=runoff,
        pipes=pipe_results,
        scenario_results=scenario_results,
        selected_pipe=selected,
        warnings=tuple(warnings),
    )
