import math

import pytest

from floodguard.runoff import RATIONAL_METHOD_FACTOR, calculate_peak_runoff
from floodguard.validation import ValidationError


def test_rational_method_reference_case():
    result = calculate_peak_runoff(5.0, 90.0, 0.75)
    assert result.peak_runoff_m3_s == pytest.approx(0.9375, rel=1e-12)
    assert result.peak_runoff_l_s == pytest.approx(937.5, rel=1e-12)


def test_rational_method_reference_is_derived_from_formula():
    result = calculate_peak_runoff(5.0, 90.0, 0.75)
    expected = 0.75 * (90.0 / 1000.0 / 3600.0) * (5.0 * 10_000.0)
    assert result.peak_runoff_m3_s == pytest.approx(expected, rel=1e-12)
    assert RATIONAL_METHOD_FACTOR == pytest.approx(1.0 / 360.0, rel=0.0, abs=0.0)


def test_result_preserves_validated_inputs():
    result = calculate_peak_runoff(2.5, 45.0, 0.4)
    assert result.catchment_area_ha == pytest.approx(2.5)
    assert result.rainfall_intensity_mm_h == pytest.approx(45.0)
    assert result.runoff_coefficient == pytest.approx(0.4)


def test_zero_runoff_coefficient_produces_zero_runoff():
    result = calculate_peak_runoff(5.0, 90.0, 0.0)
    assert result.peak_runoff_m3_s == pytest.approx(0.0, abs=1e-15)


def test_zero_rainfall_produces_zero_runoff():
    result = calculate_peak_runoff(5.0, 0.0, 0.75)
    assert result.peak_runoff_m3_s == pytest.approx(0.0, abs=1e-15)


def test_fully_impervious_catchment_is_allowed():
    result = calculate_peak_runoff(1.0, 36.0, 1.0)
    assert result.peak_runoff_m3_s == pytest.approx(0.1, rel=1e-12)


@pytest.mark.parametrize("area", [0.0, -0.001, -5.0])
def test_invalid_catchment_area_is_rejected(area):
    with pytest.raises(ValidationError, match="Catchment area"):
        calculate_peak_runoff(area, 90.0, 0.75)


@pytest.mark.parametrize("intensity", [-0.1, -90.0])
def test_negative_rainfall_intensity_is_rejected(intensity):
    with pytest.raises(ValidationError, match="Rainfall intensity"):
        calculate_peak_runoff(5.0, intensity, 0.75)


@pytest.mark.parametrize("coefficient", [-0.01, 1.01, 2.0])
def test_runoff_coefficient_outside_range_is_rejected(coefficient):
    with pytest.raises(ValidationError, match="Runoff coefficient"):
        calculate_peak_runoff(5.0, 90.0, coefficient)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", ["area", "intensity", "coefficient"])
def test_non_finite_runoff_inputs_are_rejected(bad_value, position):
    arguments = {"area": 5.0, "intensity": 90.0, "coefficient": 0.75}
    arguments[position] = bad_value
    with pytest.raises(ValidationError, match="finite"):
        calculate_peak_runoff(
            arguments["area"], arguments["intensity"], arguments["coefficient"]
        )


@pytest.mark.parametrize("bad_value", ["5", None, True])
def test_non_numeric_runoff_inputs_are_rejected(bad_value):
    with pytest.raises(ValidationError):
        calculate_peak_runoff(bad_value, 90.0, 0.75)
