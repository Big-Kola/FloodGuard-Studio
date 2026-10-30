import pytest

from floodguard.analysis import analyse_pipe, analyse_project
from floodguard.hydraulics import APPROACHING, EXCEEDS, WITHIN
from floodguard.project import create_example_project, create_starter_project


def test_project_analysis_uses_existing_engineering_core():
    project = create_starter_project("Analysis test")
    analysis = analyse_project(project, selected_pipe_id="P-01")
    assert analysis.runoff.peak_runoff_m3_s == pytest.approx(0.9375)
    assert analysis.selected_pipe is not None
    assert analysis.selected_pipe.pipe.id == "P-01"
    assert analysis.selected_pipe.hydraulics.capacity_m3_s == pytest.approx(
        1.6953454446644605
    )
    assert analysis.selected_pipe.assessment.utilisation_percent == pytest.approx(
        55.298, rel=1e-4
    )
    assert analysis.selected_pipe.assessment.classification == WITHIN
    assert len(analysis.scenario_results) == len(project.scenarios)


def test_selected_pipe_defaults_to_first_pipe():
    project = create_example_project()
    analysis = analyse_project(project)
    assert analysis.selected_pipe is not None
    assert analysis.selected_pipe.pipe.id == "P-01"


def test_unknown_selected_pipe_falls_back_to_first():
    project = create_example_project()
    analysis = analyse_project(project, selected_pipe_id="missing")
    assert analysis.selected_pipe is not None
    assert analysis.selected_pipe.pipe.id == "P-01"


def test_empty_network_analysis_is_supported():
    project = create_starter_project("Empty test")
    project.pipes = []
    analysis = analyse_project(project)
    assert analysis.selected_pipe is None
    assert analysis.network_pipe_count == 0
    assert any(item.level == "info" for item in analysis.warnings)


def test_high_utilisation_produces_critical_warning():
    project = create_starter_project("Critical test")
    pipe = project.pipes[0]
    pipe.diameter_m = 0.3
    analysis = analyse_pipe(project, pipe)
    assert analysis.assessment.classification == EXCEEDS
    result = analyse_project(project)
    assert any(item.level == "critical" for item in result.warnings)


def test_approaching_utilisation_warning():
    project = create_starter_project("Approaching test")
    pipe = project.pipes[0]
    pipe.diameter_m = 0.85
    analysis = analyse_pipe(project, pipe)
    assert analysis.assessment.classification == APPROACHING
    result = analyse_project(project)
    assert any(item.level == "warning" for item in result.warnings)
