"""Manning's equation for estimated full-flow capacity of a circular pipe."""

from __future__ import annotations

import math
from dataclasses import dataclass

from floodguard.validation import (
    percent_to_fraction,
    validate_manning_n,
    validate_non_negative_flow,
    validate_pipe_diameter,
    validate_positive_capacity,
)

WITHIN_CAPACITY_LIMIT = 80.0
EXCEEDS_CAPACITY_LIMIT = 100.0

WITHIN = "Within calculated capacity"
APPROACHING = "Approaching calculated capacity"
EXCEEDS = "Calculated demand exceeds capacity"


@dataclass(frozen=True)
class HydraulicResult:
    """Calculated full-flow geometry and capacity for a circular pipe."""

    diameter_m: float
    manning_n: float
    slope_percent: float
    slope_fraction: float
    cross_section_area_m2: float
    wetted_perimeter_m: float
    hydraulic_radius_m: float
    capacity_m3_s: float
    full_flow_velocity_m_s: float

    @property
    def capacity_l_s(self) -> float:
        """Full-flow capacity converted to litres per second."""
        return self.capacity_m3_s * 1000.0


@dataclass(frozen=True)
class CapacityAssessment:
    """Comparison of estimated peak runoff with estimated pipe capacity."""

    peak_runoff_m3_s: float
    capacity_m3_s: float
    utilisation_percent: float
    classification: str


def calculate_pipe_capacity(
    diameter_m: float,
    manning_n: float,
    slope_percent: float,
) -> HydraulicResult:
    """Estimate full-flow circular-pipe capacity using Manning's equation.

    The hydraulic energy slope is assumed equal to the specified pipe slope.
    Slope is supplied in percent and converted to a dimensionless gradient.
    """
    diameter = validate_pipe_diameter(diameter_m)
    roughness = validate_manning_n(manning_n)
    slope = percent_to_fraction(slope_percent)

    area = math.pi * diameter**2 / 4.0
    wetted_perimeter = math.pi * diameter
    hydraulic_radius = area / wetted_perimeter
    capacity = (
        (1.0 / roughness) * area * hydraulic_radius ** (2.0 / 3.0) * math.sqrt(slope)
    )
    velocity = capacity / area

    return HydraulicResult(
        diameter_m=diameter,
        manning_n=roughness,
        slope_percent=float(slope_percent),
        slope_fraction=slope,
        cross_section_area_m2=area,
        wetted_perimeter_m=wetted_perimeter,
        hydraulic_radius_m=hydraulic_radius,
        capacity_m3_s=capacity,
        full_flow_velocity_m_s=velocity,
    )


def classify_capacity(utilisation_percent: float) -> str:
    """Classify utilisation using the illustrative 80% and 100% thresholds."""
    utilisation = validate_non_negative_flow(
        utilisation_percent, "Capacity utilisation"
    )
    if utilisation < WITHIN_CAPACITY_LIMIT:
        return WITHIN
    if utilisation <= EXCEEDS_CAPACITY_LIMIT:
        return APPROACHING
    return EXCEEDS


def assess_capacity(
    peak_runoff_m3_s: float, capacity_m3_s: float
) -> CapacityAssessment:
    """Compare runoff with capacity and return utilisation and classification."""
    runoff = validate_non_negative_flow(peak_runoff_m3_s, "Peak runoff")
    capacity = validate_positive_capacity(capacity_m3_s)
    utilisation = runoff / capacity * 100.0
    return CapacityAssessment(
        peak_runoff_m3_s=runoff,
        capacity_m3_s=capacity,
        utilisation_percent=utilisation,
        classification=classify_capacity(utilisation),
    )
