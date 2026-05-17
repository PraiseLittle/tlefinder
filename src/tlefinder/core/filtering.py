"""Hard acceptance filters for candidate passes."""

from __future__ import annotations

from tlefinder.core.models import (
    CandidatePass,
    RangeConstraint,
    SearchCriteria,
    TargetToleranceConstraint,
)

_FLOAT_TOLERANCE = 1e-9


def filter_candidate_passes(
    candidates: list[CandidatePass],
    criteria: SearchCriteria,
) -> list[CandidatePass]:
    """Return candidates satisfying every enabled hard constraint."""

    accepted: list[CandidatePass] = []
    for candidate in candidates:
        rejection_reasons = _rejection_reasons(candidate, criteria)
        if rejection_reasons:
            _record_rejection_reasons(candidate, rejection_reasons)
            continue
        accepted.append(candidate)

    return accepted


def matches_culmination_constraints(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> bool:
    """Check culmination altitude range and target-tolerance constraints."""

    altitude_deg = candidate.geometry.culmination_altitude_deg
    if not _matches_range(altitude_deg, criteria.culmination_altitude_deg):
        return False

    target = criteria.culmination_altitude_target_deg
    if target is None:
        return True
    return _matches_linear_target_tolerance(
        altitude_deg,
        target,
        lower_bound=0.0,
        upper_bound=90.0,
    )


def matches_azimuth_constraints(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> bool:
    """Check start, end, and culmination azimuth target tolerances."""

    return (
        _matches_circular_target_tolerance(
            candidate.geometry.start_azimuth_deg,
            criteria.start_azimuth_deg,
        )
        and _matches_circular_target_tolerance(
            candidate.geometry.end_azimuth_deg,
            criteria.end_azimuth_deg,
        )
        and _matches_circular_target_tolerance(
            candidate.geometry.culmination_azimuth_deg,
            criteria.culmination_azimuth_deg,
        )
    )


def matches_sun_proximity_constraints(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> bool:
    """Check Sun angular-separation constraints."""

    if criteria.sun_proximity_deg is None:
        return True
    if candidate.metrics.sun_proximity_deg is None:
        return False
    return _matches_range(candidate.metrics.sun_proximity_deg, criteria.sun_proximity_deg)


def matches_satellite_altitude_constraints(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> bool:
    """Check orbital altitude constraints."""

    return _matches_range(
        candidate.metrics.satellite_altitude_km,
        criteria.satellite_altitude_km,
    )


def _rejection_reasons(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> list[str]:
    reasons: list[str] = []
    if not matches_culmination_constraints(candidate, criteria):
        reasons.append("culmination_altitude")
    if not matches_azimuth_constraints(candidate, criteria):
        reasons.append("azimuth")
    if not matches_sun_proximity_constraints(candidate, criteria):
        reasons.append("sun_proximity")
    if not matches_satellite_altitude_constraints(candidate, criteria):
        reasons.append("satellite_altitude")
    return reasons


def _record_rejection_reasons(
    candidate: CandidatePass,
    rejection_reasons: list[str],
) -> None:
    existing = candidate.diagnostics.get("rejection_reasons")
    if isinstance(existing, list):
        existing.extend(rejection_reasons)
        return
    candidate.diagnostics["rejection_reasons"] = list(rejection_reasons)


def _matches_range(value: float, constraint: RangeConstraint | None) -> bool:
    if constraint is None:
        return True
    if constraint.minimum is not None and value < constraint.minimum - _FLOAT_TOLERANCE:
        return False
    if constraint.maximum is not None and value > constraint.maximum + _FLOAT_TOLERANCE:
        return False
    return True


def _matches_linear_target_tolerance(
    value: float,
    constraint: TargetToleranceConstraint,
    *,
    lower_bound: float,
    upper_bound: float,
) -> bool:
    minimum = max(lower_bound, constraint.target - constraint.tolerance)
    maximum = min(upper_bound, constraint.target + constraint.tolerance)
    return minimum - _FLOAT_TOLERANCE <= value <= maximum + _FLOAT_TOLERANCE


def _matches_circular_target_tolerance(
    value: float,
    constraint: TargetToleranceConstraint | None,
) -> bool:
    if constraint is None:
        return True
    return _circular_distance_deg(value, constraint.target) <= (
        constraint.tolerance + _FLOAT_TOLERANCE
    )


def _circular_distance_deg(first: float, second: float) -> float:
    return abs(((first % 360.0) - (second % 360.0) + 180.0) % 360.0 - 180.0)

__all__ = [
    "filter_candidate_passes",
    "matches_azimuth_constraints",
    "matches_culmination_constraints",
    "matches_satellite_altitude_constraints",
    "matches_sun_proximity_constraints",
]
