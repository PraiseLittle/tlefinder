"""Deterministic soft-preference scoring for candidate passes."""

from __future__ import annotations

from datetime import datetime

from tlefinder.core.models import (
    CandidatePass,
    RangeConstraint,
    SearchCriteria,
    TargetToleranceConstraint,
)

_MIN_SCORE = 0.0
_MAX_SCORE = 100.0
_FLOAT_TOLERANCE = 1e-9


def compute_match_score(
    candidate: CandidatePass,
    criteria: SearchCriteria,
    interval: tuple[datetime, datetime],
) -> CandidatePass:
    """Populate and return ``candidate`` with its final 0..100 match score.

    Default duration and observable timing scores are always included.
    Declared culmination, azimuth, and Sun-proximity preferences add their
    documented component scores with equal weight. Disabled criteria contribute
    no hidden weight.
    """

    component_scores: list[float] = [
        score_pass_duration_fit(candidate, criteria, interval),
        score_pass_timing_fit(candidate, criteria, interval),
    ]

    if _culmination_scoring_enabled(criteria):
        component_scores.append(score_culmination_fit(candidate, criteria))
    if _azimuth_scoring_enabled(criteria):
        component_scores.append(score_azimuth_fit(candidate, criteria))
    if criteria.sun_proximity_deg is not None:
        component_scores.append(score_sun_proximity_fit(candidate, criteria))

    candidate.match_score = _clamp_score(sum(component_scores) / len(component_scores))

    return candidate


def score_pass_duration_fit(
    candidate: CandidatePass,
    criteria: SearchCriteria,
    interval: tuple[datetime, datetime],
) -> float:
    """Score candidate duration against the normalized search interval."""

    interval_seconds = _interval_seconds(interval)
    if interval_seconds <= _FLOAT_TOLERANCE:
        return _MIN_SCORE

    duration_seconds = (
        candidate.geometry.end_time_utc - candidate.geometry.start_time_utc
    ).total_seconds()
    return _clamp_score(_MAX_SCORE * max(0.0, duration_seconds) / interval_seconds)


def score_pass_timing_fit(
    candidate: CandidatePass,
    criteria: SearchCriteria,
    interval: tuple[datetime, datetime],
) -> float:
    """Score earlier observable starts higher inside the search interval."""

    interval_seconds = _interval_seconds(interval)
    if interval_seconds <= _FLOAT_TOLERANCE:
        return _MIN_SCORE

    observable_start = compute_observable_start_time_utc(candidate, interval[0])
    elapsed_seconds = (observable_start - interval[0]).total_seconds()
    return _clamp_score(
        _MAX_SCORE * (1.0 - (elapsed_seconds / interval_seconds))
    )


def compute_observable_start_time_utc(
    candidate: CandidatePass,
    search_start_utc: datetime,
) -> datetime:
    """Return the candidate start clipped to the search-window start."""

    return max(candidate.geometry.start_time_utc, search_start_utc)


def score_culmination_fit(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> float:
    """Score culmination altitude against declared culmination preferences."""

    altitude_deg = candidate.geometry.culmination_altitude_deg
    target = criteria.culmination_altitude_target_deg
    if target is not None:
        return _target_tolerance_score(altitude_deg, target)

    if criteria.culmination_altitude_deg is not None:
        return _range_score(
            altitude_deg,
            criteria.culmination_altitude_deg,
            domain_minimum=0.0,
            domain_maximum=90.0,
        )

    return _MAX_SCORE


def score_azimuth_fit(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> float:
    """Score start, end, and culmination azimuth target alignment."""

    scores: list[float] = []
    for value, constraint in (
        (candidate.geometry.start_azimuth_deg, criteria.start_azimuth_deg),
        (candidate.geometry.end_azimuth_deg, criteria.end_azimuth_deg),
        (
            candidate.geometry.culmination_azimuth_deg,
            criteria.culmination_azimuth_deg,
        ),
    ):
        if constraint is not None:
            scores.append(_target_tolerance_score(value, constraint, circular=True))

    if not scores:
        return _MAX_SCORE
    return _clamp_score(sum(scores) / len(scores))


def score_sun_proximity_fit(
    candidate: CandidatePass,
    criteria: SearchCriteria,
) -> float:
    """Score Sun angular-separation alignment against the declared range."""

    constraint = criteria.sun_proximity_deg
    if constraint is None:
        return _MAX_SCORE
    if candidate.metrics.sun_proximity_deg is None:
        return _MIN_SCORE
    return _range_score(
        candidate.metrics.sun_proximity_deg,
        constraint,
        domain_minimum=0.0,
        domain_maximum=180.0,
    )


def _culmination_scoring_enabled(criteria: SearchCriteria) -> bool:
    return (
        criteria.culmination_altitude_target_deg is not None
        or criteria.culmination_altitude_deg is not None
    )


def _azimuth_scoring_enabled(criteria: SearchCriteria) -> bool:
    return (
        criteria.start_azimuth_deg is not None
        or criteria.end_azimuth_deg is not None
        or criteria.culmination_azimuth_deg is not None
    )


def _target_tolerance_score(
    value: float,
    constraint: TargetToleranceConstraint,
    *,
    circular: bool = False,
) -> float:
    distance = (
        _circular_distance_deg(value, constraint.target)
        if circular
        else abs(value - constraint.target)
    )
    if constraint.tolerance <= _FLOAT_TOLERANCE:
        return _MAX_SCORE if distance <= _FLOAT_TOLERANCE else _MIN_SCORE
    return _clamp_score(
        _MAX_SCORE * (1.0 - min(distance, constraint.tolerance) / constraint.tolerance)
    )


def _range_score(
    value: float,
    constraint: RangeConstraint,
    *,
    domain_minimum: float,
    domain_maximum: float,
) -> float:
    if constraint.minimum is None and constraint.maximum is None:
        return _MAX_SCORE

    if constraint.minimum is not None and constraint.maximum is not None:
        midpoint = (constraint.minimum + constraint.maximum) / 2.0
        tolerance = (constraint.maximum - constraint.minimum) / 2.0
        return _target_tolerance_score(
            value,
            TargetToleranceConstraint(target=midpoint, tolerance=tolerance),
        )

    if constraint.minimum is not None:
        span = domain_maximum - constraint.minimum
        if span <= _FLOAT_TOLERANCE:
            return _MAX_SCORE if value >= constraint.minimum else _MIN_SCORE
        return _clamp_score(
            _MAX_SCORE * (value - constraint.minimum) / span
        )

    assert constraint.maximum is not None
    span = constraint.maximum - domain_minimum
    if span <= _FLOAT_TOLERANCE:
        return _MAX_SCORE if value <= constraint.maximum else _MIN_SCORE
    return _clamp_score(
        _MAX_SCORE * (constraint.maximum - value) / span
    )


def _circular_distance_deg(first: float, second: float) -> float:
    return abs(((first % 360.0) - (second % 360.0) + 180.0) % 360.0 - 180.0)


def _interval_seconds(interval: tuple[datetime, datetime]) -> float:
    return (interval[1] - interval[0]).total_seconds()


def _clamp_score(value: float) -> float:
    return max(_MIN_SCORE, min(_MAX_SCORE, float(value)))


__all__ = [
    "compute_observable_start_time_utc",
    "compute_match_score",
    "score_azimuth_fit",
    "score_culmination_fit",
    "score_pass_duration_fit",
    "score_pass_timing_fit",
    "score_sun_proximity_fit",
]
