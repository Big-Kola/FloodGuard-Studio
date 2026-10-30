import math

import pytest

from floodguard.hydraulics import (
    APPROACHING,
    EXCEEDS,
    WITHIN,
    assess_capacity,
    calculate_pipe_capacity,
    classify_capacity,
)
from floodguard.validation import ValidationError


def test_manning_reference_case():
    result = calculate_pipe_capacity(1.0, 0.013, 0.5)
    assert result.capacity_m3_s == pytest.approx(1.6953454446644605, rel=1e-9)


def test_full_pipe_geometry():
    result = calculate_pipe_capacity(1.0, 0.013, 0.5)
    assert result.cross_section_area_m2 == pytest.approx(math.pi / 4.0, rel=1e-12)
    assert result.wetted_perimeter_m == pytest.approx(math.pi, rel=1e-12)
    assert result.hydraulic_radius_m == pytest.approx(0.25, rel=1e-12)
    assert result.hydraulic_radius_m == pytest.approx(
        result.diameter_m / 4.0, rel=1e-12
    )


def test_manning_reference_is_derived_from_formula():
    diameter = 1.0
    n = 0.013
    slope = 0.005
    area = math.pi * diameter**2 / 4.0
    radius = diameter / 4.0
    expected = (1.0 / n) * area * radius ** (2.0 / 3.0) * math.sqrt(slope)
    result = calculate_pipe_capacity(diameter, n, 0.5)
    assert result.capacity_m3_s == pytest.approx(expected, rel=1e-12)


def test_full_flow_velocity_is_capacity_over_area():
    result = calculate_pipe_capacity(1.0, 0.013, 0.5)
    assert result.full_flow_velocity_m_s == pytest.approx(
        result.capacity_m3_s / result.cross_section_area_m2, rel=1e-12
    )
    assert result.full_flow_velocity_m_s == pytest.approx(2.1585808621334097, rel=1e-9)


def test_slope_percentage_conversion():
    result = calculate_pipe_capacity(1.0, 0.013, 0.5)
    assert result.slope_fraction == pytest.approx(0.005, rel=1e-12)
    assert result.slope_percent == pytest.approx(0.5, rel=1e-12)


def test_percentage_and_dimensionless_slope_are_not_confused():
    result = calculate_pipe_capacity(1.0, 0.013, 1.0)
    assert result.slope_fraction == pytest.approx(0.01, rel=1e-12)
    wrong_slope_result = calculate_pipe_capacity(1.0, 0.013, 100.0)
    assert result.capacity_m3_s == pytest.approx(
        wrong_slope_result.capacity_m3_s / 10.0, rel=1e-12
    )


def test_capacity_increases_with_diameter():
    small = calculate_pipe_capacity(1.0, 0.013, 0.5)
    large = calculate_pipe_capacity(1.2, 0.013, 0.5)
    assert large.capacity_m3_s > small.capacity_m3_s


def test_capacity_increases_with_slope():
    flat = calculate_pipe_capacity(1.0, 0.013, 0.5)
    steep = calculate_pipe_capacity(1.0, 0.013, 1.0)
    assert steep.capacity_m3_s > flat.capacity_m3_s


@pytest.mark.parametrize("diameter", [0.0, -0.5, -1.0])
def test_invalid_pipe_diameter_is_rejected(diameter):
    with pytest.raises(ValidationError, match="Pipe diameter"):
        calculate_pipe_capacity(diameter, 0.013, 0.5)


@pytest.mark.parametrize("roughness", [0.0, -0.013])
def test_invalid_manning_n_is_rejected(roughness):
    with pytest.raises(ValidationError, match="Manning"):
        calculate_pipe_capacity(1.0, roughness, 0.5)


@pytest.mark.parametrize("slope", [0.0, -0.5, -5.0])
def test_zero_or_negative_slope_is_rejected(slope):
    with pytest.raises(ValidationError, match="Pipe slope"):
        calculate_pipe_capacity(1.0, 0.013, slope)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", ["diameter", "roughness", "slope"])
def test_non_finite_hydraulic_inputs_are_rejected(bad_value, position):
    arguments = {"diameter": 1.0, "roughness": 0.013, "slope": 0.5}
    arguments[position] = bad_value
    with pytest.raises(ValidationError, match="finite"):
        calculate_pipe_capacity(
            arguments["diameter"], arguments["roughness"], arguments["slope"]
        )


@pytest.mark.parametrize(
    ("utilisation", "expected"),
    [
        (0.0, WITHIN),
        (79.999999, WITHIN),
        (80.0, APPROACHING),
        (99.999999, APPROACHING),
        (100.0, APPROACHING),
        (100.000001, EXCEEDS),
        (250.0, EXCEEDS),
    ],
)
def test_classification_boundaries(utilisation, expected):
    assert classify_capacity(utilisation) == expected


def test_assess_capacity_calculates_utilisation():
    assessment = assess_capacity(0.5, 1.0)
    assert assessment.utilisation_percent == pytest.approx(50.0)
    assert assessment.classification == WITHIN


def test_assess_capacity_at_exactly_100_percent():
    assessment = assess_capacity(1.0, 1.0)
    assert assessment.utilisation_percent == pytest.approx(100.0)
    assert assessment.classification == APPROACHING


def test_assess_capacity_above_capacity():
    assessment = assess_capacity(1.1, 1.0)
    assert assessment.utilisation_percent == pytest.approx(110.0)
    assert assessment.classification == EXCEEDS


def test_assess_capacity_with_zero_runoff():
    assessment = assess_capacity(0.0, 1.0)
    assert assessment.utilisation_percent == pytest.approx(0.0)
    assert assessment.classification == WITHIN


@pytest.mark.parametrize("capacity", [0.0, -1.0])
def test_capacity_assessment_requires_positive_capacity(capacity):
    with pytest.raises(ValidationError, match="Pipe capacity"):
        assess_capacity(0.5, capacity)


def test_capacity_assessment_rejects_negative_runoff():
    with pytest.raises(ValidationError, match="Peak runoff"):
        assess_capacity(-0.1, 1.0)


def test_classification_rejects_negative_utilisation():
    with pytest.raises(ValidationError, match="Capacity utilisation"):
        classify_capacity(-1.0)
