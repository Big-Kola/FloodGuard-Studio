"""Rational Method implementation for preliminary peak stormwater runoff."""

from __future__ import annotations

from dataclasses import dataclass

from floodguard.validation import (
    validate_catchment_area,
    validate_rainfall_intensity,
    validate_runoff_coefficient,
)

RATIONAL_METHOD_FACTOR = 1.0 / 360.0


@dataclass(frozen=True)
class RunoffResult:
    """Calculated peak runoff and the validated inputs used to obtain it."""

    catchment_area_ha: float
    rainfall_intensity_mm_h: float
    runoff_coefficient: float
    peak_runoff_m3_s: float

    @property
    def peak_runoff_l_s(self) -> float:
        """Peak runoff converted to litres per second."""
        return self.peak_runoff_m3_s * 1000.0


def calculate_peak_runoff(
    catchment_area_ha: float,
    rainfall_intensity_mm_h: float,
    runoff_coefficient: float,
) -> RunoffResult:
    """Estimate peak runoff using Q = (1/360) C I A in SI-compatible units.

    Parameters
    ----------
    catchment_area_ha:
        Contributing catchment area in hectares.
    rainfall_intensity_mm_h:
        Design rainfall intensity in millimetres per hour.
    runoff_coefficient:
        Dimensionless runoff coefficient in the range 0 to 1.
    """
    area = validate_catchment_area(catchment_area_ha)
    intensity = validate_rainfall_intensity(rainfall_intensity_mm_h)
    coefficient = validate_runoff_coefficient(runoff_coefficient)

    peak_runoff = RATIONAL_METHOD_FACTOR * coefficient * intensity * area
    return RunoffResult(
        catchment_area_ha=area,
        rainfall_intensity_mm_h=intensity,
        runoff_coefficient=coefficient,
        peak_runoff_m3_s=peak_runoff,
    )
