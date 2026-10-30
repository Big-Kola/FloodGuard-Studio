import math

import pytest

from floodguard.validation import (
    ValidationError,
    percent_to_fraction,
    require_finite,
    validate_catchment_area,
    validate_manning_n,
    validate_non_negative_flow,
    validate_pipe_diameter,
    validate_positive_capacity,
    validate_rainfall_intensity,
    validate_runoff_coefficient,
    validate_slope_percent,
)


def test_validation_error_is_a_value_error():
    assert issubclass(ValidationError, ValueError)


def test_require_finite_accepts_integers_and_floats():
    assert require_finite(3, "value") == pytest.approx(3.0)
    assert require_finite(3.5, "value") == pytest.approx(3.5)


@pytest.mark.parametrize("bad_value", ["3.5", None, True, False, [1.0]])
def test_require_finite_rejects_non_numeric_values(bad_value):
    with pytest.raises(ValidationError, match="numeric"):
        require_finite(bad_value, "Test value")


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_require_finite_rejects_non_finite_values(bad_value):
    with pytest.raises(ValidationError, match="finite"):
        require_finite(bad_value, "Test value")


def test_validators_accept_valid_values():
    assert validate_catchment_area(5.0) == pytest.approx(5.0)
    assert validate_rainfall_intensity(0.0) == pytest.approx(0.0)
    assert validate_runoff_coefficient(0.0) == pytest.approx(0.0)
    assert validate_runoff_coefficient(1.0) == pytest.approx(1.0)
    assert validate_pipe_diameter(1.0) == pytest.approx(1.0)
    assert validate_manning_n(0.013) == pytest.approx(0.013)
    assert validate_slope_percent(0.5) == pytest.approx(0.5)
    assert validate_non_negative_flow(0.0) == pytest.approx(0.0)
    assert validate_positive_capacity(1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_catchment_area_must_be_positive(value):
    with pytest.raises(ValidationError, match="greater than 0"):
        validate_catchment_area(value)


def test_rainfall_intensity_must_not_be_negative():
    with pytest.raises(ValidationError, match="negative"):
        validate_rainfall_intensity(-0.1)


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_runoff_coefficient_must_be_in_range(value):
    with pytest.raises(ValidationError, match="between 0 and 1"):
        validate_runoff_coefficient(value)


def test_pipe_diameter_must_be_positive():
    with pytest.raises(ValidationError, match="greater than 0"):
        validate_pipe_diameter(0.0)


def test_manning_n_must_be_positive():
    with pytest.raises(ValidationError, match="greater than 0"):
        validate_manning_n(0.0)


def test_slope_must_be_positive():
    with pytest.raises(ValidationError, match="greater than 0"):
        validate_slope_percent(0.0)


def test_percent_to_fraction_conversion():
    assert percent_to_fraction(0.5) == pytest.approx(0.005, rel=1e-12)
    assert percent_to_fraction(1.0) == pytest.approx(0.01, rel=1e-12)
    assert percent_to_fraction(100.0) == pytest.approx(1.0, rel=1e-12)


def test_percent_to_fraction_rejects_invalid_slope():
    with pytest.raises(ValidationError):
        percent_to_fraction(-0.5)


def test_non_negative_flow_rejects_negative_values():
    with pytest.raises(ValidationError, match="must not be negative"):
        validate_non_negative_flow(-0.001, "Runoff")


def test_positive_capacity_rejects_zero():
    with pytest.raises(ValidationError, match="greater than 0"):
        validate_positive_capacity(0.0)
