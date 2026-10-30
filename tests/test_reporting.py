from datetime import datetime

import pandas as pd
import pytest

from floodguard.analysis import analyse_project
from floodguard.hydraulics import assess_capacity, calculate_pipe_capacity
from floodguard.project import create_example_project, create_starter_project
from floodguard.reporting import (
    build_pdf_report,
    build_pipe_results_csv,
    build_scenario_csv,
    build_studio_pdf_report,
    scenario_results_to_dataframe,
)
from floodguard.runoff import calculate_peak_runoff
from floodguard.scenarios import default_scenarios, evaluate_scenarios


@pytest.fixture
def current_case():
    runoff = calculate_peak_runoff(5.0, 90.0, 0.75)
    hydraulics = calculate_pipe_capacity(1.0, 0.013, 0.5)
    assessment = assess_capacity(runoff.peak_runoff_m3_s, hydraulics.capacity_m3_s)
    return runoff, hydraulics, assessment


@pytest.fixture
def scenario_results():
    return evaluate_scenarios(default_scenarios())


def test_scenario_dataframe_contains_calculated_values(scenario_results):
    dataframe = scenario_results_to_dataframe(scenario_results)
    assert isinstance(dataframe, pd.DataFrame)
    assert len(dataframe) == len(scenario_results)
    expected = scenario_results[0]
    row = dataframe.iloc[0]
    assert row["Scenario"] == expected.name
    assert row["Peak runoff (m3/s)"] == pytest.approx(expected.runoff.peak_runoff_m3_s)
    assert row["Pipe capacity (m3/s)"] == pytest.approx(
        expected.hydraulics.capacity_m3_s
    )
    assert row["Capacity utilisation (%)"] == pytest.approx(
        expected.assessment.utilisation_percent
    )
    assert row["Classification"] == expected.assessment.classification


def test_scenario_dataframe_has_required_columns(scenario_results):
    dataframe = scenario_results_to_dataframe(scenario_results)
    required = {
        "Scenario",
        "Rainfall intensity (mm/h)",
        "Catchment area (ha)",
        "Runoff coefficient",
        "Pipe diameter (m)",
        "Pipe capacity (m3/s)",
        "Peak runoff (m3/s)",
        "Capacity utilisation (%)",
        "Classification",
    }
    assert required.issubset(set(dataframe.columns))


def test_csv_generation(scenario_results):
    payload = build_scenario_csv(scenario_results)
    assert isinstance(payload, bytes)
    assert payload.startswith(b"\xef\xbb\xbf")
    text = payload.decode("utf-8-sig")
    assert text.startswith("Scenario,Catchment area (ha),Runoff coefficient")
    assert "Existing drainage configuration" in text
    assert "Capacity utilisation (%)" in text
    assert text.count("\n") >= len(scenario_results)


def test_csv_generation_of_empty_results_is_not_used_by_ui_but_is_well_formed():
    payload = build_scenario_csv([])
    text = payload.decode("utf-8-sig")
    assert "Scenario" in text.splitlines()[0]


def test_pdf_generation_with_scenarios(current_case, scenario_results):
    runoff, hydraulics, assessment = current_case
    payload = build_pdf_report(
        runoff,
        hydraulics,
        assessment,
        scenario_results,
        generated_at=datetime(2026, 10, 26, 12, 0),
    )
    assert payload.startswith(b"%PDF")
    assert payload.rstrip().endswith(b"%%EOF")
    assert len(payload) > 3000


def test_pdf_generation_without_scenarios(current_case):
    runoff, hydraulics, assessment = current_case
    payload = build_pdf_report(runoff, hydraulics, assessment)
    assert payload.startswith(b"%PDF")
    assert len(payload) > 2500


def test_pdf_contains_report_title_metadata(current_case):
    runoff, hydraulics, assessment = current_case
    payload = build_pdf_report(runoff, hydraulics, assessment)
    assert b"FloodGuard Studio" in payload


def test_studio_pdf_report_contains_project_and_pipe_results():
    project = create_example_project()
    analysis = analyse_project(project)
    payload = build_studio_pdf_report(
        project,
        analysis,
        generated_at=datetime(2026, 10, 26, 12, 0),
    )
    assert payload.startswith(b"%PDF")
    assert payload.rstrip().endswith(b"%%EOF")
    assert b"FloodGuard Studio" in payload
    assert b"Riverside Demonstration Catchment" in payload
    assert len(payload) > 4000


def test_pipe_results_csv_matches_analysis():
    project = create_example_project()
    analysis = analyse_project(project)
    payload = build_pipe_results_csv(analysis)
    text = payload.decode("utf-8-sig")
    assert text.startswith("Pipe,ID,From node")
    assert "Reach J1-J2" in text
    assert "Capacity utilisation (%)" in text
    assert text.count("\n") == len(project.pipes) + 1


def test_pipe_results_csv_without_pipes_retains_header():
    project = create_starter_project("No pipes")
    project.pipes = []
    analysis = analyse_project(project)
    text = build_pipe_results_csv(analysis).decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Pipe,ID,From node")
    assert len(text.splitlines()) == 1
