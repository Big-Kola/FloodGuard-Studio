"""Input validation shared by the engineering modules and the desktop UI."""

from __future__ import annotations

import math
from numbers import Real


class ValidationError(ValueError):
    """Raised when an engineering input is missing, non-finite or out of range."""


def require_finite(value: object, field_name: str, unit: str = "") -> float:
    """Return *value* as a finite float or raise a descriptive ValidationError."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{field_name} must be a numeric value.")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{field_name} must be a finite number.")
    return number


def validate_catchment_area(area_ha: object) -> float:
    """Validate a catchment area in hectares (> 0)."""
    area = require_finite(area_ha, "Catchment area", "ha")
    if area <= 0.0:
        raise ValidationError("Catchment area must be greater than 0 ha.")
    return area


def validate_rainfall_intensity(intensity_mm_h: object) -> float:
    """Validate rainfall intensity in mm/h (>= 0)."""
    intensity = require_finite(intensity_mm_h, "Rainfall intensity", "mm/h")
    if intensity < 0.0:
        raise ValidationError("Rainfall intensity must not be negative.")
    return intensity


def validate_runoff_coefficient(coefficient: object) -> float:
    """Validate a dimensionless runoff coefficient in the closed interval [0, 1]."""
    value = require_finite(coefficient, "Runoff coefficient")
    if value < 0.0 or value > 1.0:
        raise ValidationError("Runoff coefficient must be between 0 and 1.")
    return value


def validate_pipe_diameter(diameter_m: object) -> float:
    """Validate an internal pipe diameter in metres (> 0)."""
    diameter = require_finite(diameter_m, "Pipe diameter", "m")
    if diameter <= 0.0:
        raise ValidationError("Pipe diameter must be greater than 0 m.")
    return diameter


def validate_manning_n(manning_n: object) -> float:
    """Validate Manning's roughness coefficient (> 0)."""
    value = require_finite(manning_n, "Manning roughness coefficient")
    if value <= 0.0:
        raise ValidationError("Manning roughness coefficient must be greater than 0.")
    return value


def validate_slope_percent(slope_percent: object) -> float:
    """Validate a pipe slope expressed in percent (> 0)."""
    slope = require_finite(slope_percent, "Pipe slope", "%")
    if slope <= 0.0:
        raise ValidationError("Pipe slope must be greater than 0% for this model.")
    return slope


def percent_to_fraction(slope_percent: object) -> float:
    """Convert a valid slope in percent to a dimensionless m/m gradient."""
    return validate_slope_percent(slope_percent) / 100.0


def validate_non_negative_flow(value: object, field_name: str = "Flow") -> float:
    """Validate a flow value in m3/s (>= 0)."""
    flow = require_finite(value, field_name, "m3/s")
    if flow < 0.0:
        raise ValidationError(f"{field_name} must not be negative.")
    return flow


def validate_positive_capacity(capacity_m3_s: object) -> float:
    """Validate a pipe capacity in m3/s (> 0)."""
    capacity = require_finite(capacity_m3_s, "Pipe capacity", "m3/s")
    if capacity <= 0.0:
        raise ValidationError("Pipe capacity must be greater than 0 m3/s.")
    return capacity
