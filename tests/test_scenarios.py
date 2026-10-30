import math

import pandas as pd
import pytest

from floodguard.hydraulics import assess_capacity, calculate_pipe_capacity
from floodguard.runoff import calculate_peak_runoff
from floodguard.scenarios import (
    DEFAULT_SCENARIOS,
    Scenario,
    dataframe_to_scenarios,
    default_scenarios,
    default_scenarios_dataframe,
    evaluate_scenario,
    evaluate_scenarios,
    scenarios_to_dataframe,
)
from floodguard.validation import ValidationError


def test_at_least_three_built_in_scenarios():
    scenarios = default_scenarios()
    assert len(scenarios) >= 3
    assert len({scenario.name for scenario in scenarios}) == len(scenarios)


def test_built_in_scenario_names_cover_required_cases():
    names = " ".join(scenario.name.lower() for scenario in default_scenarios())
    assert "existing" in names
    assert "rainfall" in names
    assert "pipe" in names


def test_scenario_evaluation_matches_core_functions():
    scenario = DEFAULT_SCENARIOS[0]
    result = evaluate_scenario(scenario)
    expected_runoff = calculate_peak_runoff(
        scenario.catchment_area_ha,
        scenario.rainfall_intensity_mm_h,
        scenario.runoff_coefficient,
    )
    expected_hydraulics = calculate_pipe_capacity(
        scenario.pipe_diameter_m,
        scenario.manning_n,
        scenario.slope_percent,
    )
    expected_assessment = assess_capacity(
        expected_runoff.peak_runoff_m3_s, expected_hydraulics.capacity_m3_s
    )
    assert result.runoff == expected_runoff
    assert result.hydraulics == expected_hydraulics
    assert result.assessment == expected_assessment


def test_all_built_in_scenarios_evaluate_successfully():
    results = evaluate_scenarios(default_scenarios())
    assert len(results) == len(DEFAULT_SCENARIOS)
    assert all(result.assessment.utilisation_percent >= 0.0 for result in results)


def test_baseline_reference_values():
    result = evaluate_scenarios(default_scenarios())[0]
    assert result.runoff.peak_runoff_m3_s == pytest.approx(0.9375, rel=1e-12)
    assert result.hydraulics.capacity_m3_s == pytest.approx(
        1.6953454446644605, rel=1e-9
    )
    assert result.assessment.utilisation_percent == pytest.approx(55.298, rel=1e-4)


def test_increased_rainfall_produces_more_runoff_and_higher_utilisation():
    baseline, increased, _ = evaluate_scenarios(default_scenarios())
    assert increased.runoff.peak_runoff_m3_s > baseline.runoff.peak_runoff_m3_s
    assert (
        increased.assessment.utilisation_percent
        > baseline.assessment.utilisation_percent
    )


def test_larger_pipe_increases_capacity_and_reduces_utilisation():
    baseline, _, upsized = evaluate_scenarios(default_scenarios())
    assert upsized.hydraulics.capacity_m3_s > baseline.hydraulics.capacity_m3_s
    assert (
        upsized.assessment.utilisation_percent < baseline.assessment.utilisation_percent
    )


def test_dataframe_roundtrip_preserves_inputs():
    dataframe = default_scenarios_dataframe()
    scenarios = dataframe_to_scenarios(dataframe)
    assert len(scenarios) == len(DEFAULT_SCENARIOS)
    for scenario, expected in zip(scenarios, DEFAULT_SCENARIOS):
        assert scenario.name == expected.name
        assert scenario.catchment_area_ha == pytest.approx(expected.catchment_area_ha)
        assert scenario.rainfall_intensity_mm_h == pytest.approx(
            expected.rainfall_intensity_mm_h
        )


def test_scenarios_to_dataframe_has_expected_columns():
    dataframe = scenarios_to_dataframe(default_scenarios())
    assert list(dataframe.columns) == [
        "Scenario",
        "Catchment area (ha)",
        "Runoff coefficient",
        "Rainfall intensity (mm/h)",
        "Pipe diameter (m)",
        "Manning n",
        "Slope (%)",
        "Description",
    ]
    assert len(dataframe) == len(DEFAULT_SCENARIOS)


def test_custom_scenario_is_calculated_dynamically():
    scenario = Scenario(
        name="Custom test",
        catchment_area_ha=2.0,
        runoff_coefficient=0.5,
        rainfall_intensity_mm_h=60.0,
        pipe_diameter_m=0.8,
        manning_n=0.015,
        slope_percent=1.0,
    )
    result = evaluate_scenario(scenario)
    expected_runoff = (1.0 / 360.0) * 0.5 * 60.0 * 2.0
    assert result.runoff.peak_runoff_m3_s == pytest.approx(expected_runoff, rel=1e-12)
    assert result.assessment.utilisation_percent == pytest.approx(
        expected_runoff / result.hydraulics.capacity_m3_s * 100.0, rel=1e-12
    )


def test_empty_scenario_table_is_rejected():
    with pytest.raises(ValidationError, match="At least one scenario"):
        dataframe_to_scenarios(default_scenarios_dataframe().iloc[0:0])


def test_blank_extra_rows_are_ignored():
    dataframe = default_scenarios_dataframe()
    blank = pd.DataFrame([{column: None for column in dataframe.columns}])
    combined = pd.concat([dataframe, blank], ignore_index=True)
    scenarios = dataframe_to_scenarios(combined)
    assert len(scenarios) == len(DEFAULT_SCENARIOS)


def test_named_row_with_missing_numeric_value_is_rejected():
    dataframe = default_scenarios_dataframe()
    dataframe.loc[0, "Pipe diameter (m)"] = math.nan
    scenario = dataframe_to_scenarios(dataframe)[0]
    with pytest.raises(ValidationError, match="Pipe diameter"):
        evaluate_scenario(scenario)


def test_row_without_name_is_rejected():
    dataframe = default_scenarios_dataframe()
    dataframe.loc[0, "Scenario"] = "  "
    with pytest.raises(ValidationError, match="requires a name"):
        dataframe_to_scenarios(dataframe)


def test_non_numeric_scenario_value_is_rejected():
    dataframe = default_scenarios_dataframe()
    dataframe["Rainfall intensity (mm/h)"] = dataframe[
        "Rainfall intensity (mm/h)"
    ].astype(object)
    dataframe.loc[0, "Rainfall intensity (mm/h)"] = "ninety"
    with pytest.raises(ValidationError, match="rainfall intensity"):
        dataframe_to_scenarios(dataframe)


def test_missing_column_is_rejected():
    dataframe = default_scenarios_dataframe().drop(columns=["Manning n"])
    with pytest.raises(ValidationError, match="missing columns"):
        dataframe_to_scenarios(dataframe)


def test_scenario_evaluation_rejects_invalid_core_inputs():
    scenario = Scenario(
        name="Invalid",
        catchment_area_ha=-1.0,
        runoff_coefficient=0.75,
        rainfall_intensity_mm_h=90.0,
        pipe_diameter_m=1.0,
        manning_n=0.013,
        slope_percent=0.5,
    )
    with pytest.raises(ValidationError):
        evaluate_scenario(scenario)
