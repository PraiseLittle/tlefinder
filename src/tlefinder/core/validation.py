"""Validation guards for phase 2 search requests."""

from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from numbers import Real
from typing import Any

from tlefinder.core.errors import ValidationError
from tlefinder.core.models import (
    GroundStation,
    RangeConstraint,
    SatelliteGroup,
    SearchCriteria,
    SearchRequest,
    SearchWindow,
    TargetToleranceConstraint,
)

MAX_SEARCH_DURATION_MINUTES = 30.0
MIN_GROUND_ELEVATION_M = -500.0
MAX_GROUND_ELEVATION_M = 8_000.0
MIN_SATELLITE_ALTITUDE_KM = 200.0
MAX_SATELLITE_ALTITUDE_KM = 15_000.0
SUPPORTED_SATELLITE_GROUPS = frozenset(
    {
        SatelliteGroup.ACTIVE,
        SatelliteGroup.VISUAL,
        SatelliteGroup.AMATEUR,
    }
)


def validate_search_request(request: SearchRequest) -> None:
    """Validate the complete shared request model."""

    if not isinstance(request, SearchRequest):
        raise ValidationError("request must be a SearchRequest")

    validate_satellite_group(request.satellite_group)
    validate_ground_station(request.station)
    validate_search_window(request.window)
    validate_search_criteria(request.criteria)


def validate_satellite_group(group: SatelliteGroup) -> None:
    """Validate that ``group`` is one of the supported TLE source groupings."""

    if not isinstance(group, SatelliteGroup) or group not in SUPPORTED_SATELLITE_GROUPS:
        supported = ", ".join(
            supported_group.value
            for supported_group in sorted(
                SUPPORTED_SATELLITE_GROUPS,
                key=lambda supported_group: supported_group.value,
            )
        )
        raise ValidationError(f"satellite_group must be one of: {supported}")


def validate_ground_station(station: GroundStation) -> None:
    """Validate optical ground-station coordinates and elevation."""

    if not isinstance(station, GroundStation):
        raise ValidationError("station must be a GroundStation")

    latitude = _require_finite_number("latitude", station.latitude)
    if not -90.0 <= latitude <= 90.0:
        raise ValidationError("latitude must be within [-90, 90] degrees")

    longitude = _require_finite_number("longitude", station.longitude)
    if not -180.0 <= longitude <= 180.0:
        raise ValidationError("longitude must be within [-180, 180] degrees")

    elevation_m = _require_finite_number("elevation", station.elevation_m)
    if not MIN_GROUND_ELEVATION_M <= elevation_m <= MAX_GROUND_ELEVATION_M:
        raise ValidationError(
            "elevation must be within [-500, 8000] meters for a ground station"
        )


def validate_search_window(window: SearchWindow) -> None:
    """Validate search-window duration and explicit timezone handling."""

    if not isinstance(window, SearchWindow):
        raise ValidationError("window must be a SearchWindow")
    if not isinstance(window.start_at, datetime):
        raise ValidationError("start_at must be a datetime")
    if not _is_timezone_aware(window.start_at):
        raise ValidationError("start_at must include an explicit timezone")
    if not _has_fixed_utc_offset(window.start_at):
        raise ValidationError(
            "start_at timezone must be UTC or a fixed UTC offset"
        )

    duration_minutes = _require_finite_number("duration", window.duration_minutes)
    if duration_minutes <= 0.0:
        raise ValidationError("duration must be greater than 0 minutes")
    if duration_minutes > MAX_SEARCH_DURATION_MINUTES:
        raise ValidationError("duration must not exceed 30 minutes")


def validate_search_criteria(criteria: SearchCriteria) -> None:
    """Validate phase 2 hard constraints and ranking controls."""

    if not isinstance(criteria, SearchCriteria):
        raise ValidationError("criteria must be a SearchCriteria")

    _validate_range_constraint(
        "culmination_altitude_deg",
        criteria.culmination_altitude_deg,
        lower=0.0,
        upper=90.0,
    )
    _validate_target_tolerance_constraint(
        "culmination_altitude_target_deg",
        criteria.culmination_altitude_target_deg,
        target_lower=0.0,
        target_upper=90.0,
        tolerance_lower=0.0,
        tolerance_upper=90.0,
    )
    for name, constraint in (
        ("start_azimuth_deg", criteria.start_azimuth_deg),
        ("end_azimuth_deg", criteria.end_azimuth_deg),
        ("culmination_azimuth_deg", criteria.culmination_azimuth_deg),
    ):
        _validate_target_tolerance_constraint(
            name,
            constraint,
            target_lower=0.0,
            target_upper=360.0,
            target_upper_inclusive=False,
            tolerance_lower=0.0,
            tolerance_upper=180.0,
        )

    _validate_range_constraint(
        "sun_proximity_deg",
        criteria.sun_proximity_deg,
        lower=0.0,
        upper=180.0,
    )
    _validate_range_constraint(
        "satellite_altitude_km",
        criteria.satellite_altitude_km,
        lower=MIN_SATELLITE_ALTITUDE_KM,
        upper=MAX_SATELLITE_ALTITUDE_KM,
    )

    score_threshold = _require_finite_number(
        "score_threshold", criteria.score_threshold
    )
    if not 0.0 <= score_threshold <= 100.0:
        raise ValidationError("score_threshold must be within [0, 100]")

    if isinstance(criteria.result_limit, bool) or not isinstance(
        criteria.result_limit, int
    ):
        raise ValidationError("result_limit must be an integer")
    if criteria.result_limit <= 0:
        raise ValidationError("result_limit must be strictly positive")


def _validate_range_constraint(
    name: str,
    constraint: RangeConstraint | None,
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> None:
    if constraint is None:
        return
    if not isinstance(constraint, RangeConstraint):
        raise ValidationError(f"{name} must be a RangeConstraint")

    minimum = _optional_finite_number(f"{name}.minimum", constraint.minimum)
    maximum = _optional_finite_number(f"{name}.maximum", constraint.maximum)

    if minimum is not None and lower is not None and minimum < lower:
        raise ValidationError(f"{name} minimum must be at least {lower:g}")
    if maximum is not None and lower is not None and maximum < lower:
        raise ValidationError(f"{name} maximum must be at least {lower:g}")
    if minimum is not None and upper is not None and minimum > upper:
        raise ValidationError(f"{name} minimum must be at most {upper:g}")
    if maximum is not None and upper is not None and maximum > upper:
        raise ValidationError(f"{name} maximum must be at most {upper:g}")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValidationError(f"{name} minimum must not be greater than maximum")


def _validate_target_tolerance_constraint(
    name: str,
    constraint: TargetToleranceConstraint | None,
    *,
    target_lower: float,
    target_upper: float,
    tolerance_lower: float,
    tolerance_upper: float,
    target_upper_inclusive: bool = True,
) -> None:
    if constraint is None:
        return
    if not isinstance(constraint, TargetToleranceConstraint):
        raise ValidationError(f"{name} must be a TargetToleranceConstraint")

    target = _require_finite_number(f"{name}.target", constraint.target)
    tolerance = _require_finite_number(f"{name}.tolerance", constraint.tolerance)

    if target < target_lower:
        raise ValidationError(f"{name} target must be at least {target_lower:g}")
    if target_upper_inclusive:
        target_is_too_high = target > target_upper
        comparison = "at most"
    else:
        target_is_too_high = target >= target_upper
        comparison = "less than"
    if target_is_too_high:
        raise ValidationError(f"{name} target must be {comparison} {target_upper:g}")
    if not tolerance_lower <= tolerance <= tolerance_upper:
        raise ValidationError(
            f"{name} tolerance must be within "
            f"[{tolerance_lower:g}, {tolerance_upper:g}]"
        )


def _optional_finite_number(name: str, value: Any) -> float | None:
    if value is None:
        return None
    return _require_finite_number(name, value)


def _require_finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValidationError(f"{name} must be numeric")
    number = float(value)
    if not isfinite(number):
        raise ValidationError(f"{name} must be finite")
    return number


def _is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _has_fixed_utc_offset(value: datetime) -> bool:
    return isinstance(value.tzinfo, timezone)


__all__ = [
    "MAX_SEARCH_DURATION_MINUTES",
    "MAX_GROUND_ELEVATION_M",
    "MAX_SATELLITE_ALTITUDE_KM",
    "MIN_GROUND_ELEVATION_M",
    "MIN_SATELLITE_ALTITUDE_KM",
    "SUPPORTED_SATELLITE_GROUPS",
    "validate_ground_station",
    "validate_satellite_group",
    "validate_search_criteria",
    "validate_search_request",
    "validate_search_window",
]
