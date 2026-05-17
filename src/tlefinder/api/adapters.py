"""Conversion boundary between API schemas and core search models."""

from __future__ import annotations

from tlefinder.api import schemas as api_schemas
from tlefinder.core import models as core_models

_SIMPLE_CULMINATION_ALTITUDE_DEG = (0.0, 90.0)
_SIMPLE_SUN_PROXIMITY_DEG = (0.0, 180.0)
_SIMPLE_SATELLITE_ALTITUDE_KM = (200.0, 2000.0)
_DEFAULT_RESULT_LIMIT = 10
_DISABLED_SCORE_THRESHOLD = 0.0


def simple_search_to_core_request(
    request: api_schemas.SimpleSearchRequest,
) -> core_models.SearchRequest:
    """Adapt a simple API search request into the shared core request model."""
    return core_models.SearchRequest(
        station=_station_to_core(request.station),
        window=_window_to_core(request.window),
        criteria=_simple_search_criteria(),
        satellite_group=core_models.SatelliteGroup.ACTIVE,
    )


def advanced_search_to_core_request(
    request: api_schemas.AdvancedSearchRequest,
) -> core_models.SearchRequest:
    """Adapt an advanced API search request into the shared core request model."""
    criteria = request.criteria
    return core_models.SearchRequest(
        station=_station_to_core(request.station),
        window=_window_to_core(request.window),
        criteria=core_models.SearchCriteria(
            culmination_altitude_deg=_range_to_core(
                criteria.culmination_altitude_deg
            ),
            culmination_altitude_target_deg=_target_tolerance_to_core(
                criteria.culmination_altitude_target_deg
            ),
            start_azimuth_deg=_target_tolerance_to_core(criteria.start_azimuth_deg),
            end_azimuth_deg=_target_tolerance_to_core(criteria.end_azimuth_deg),
            culmination_azimuth_deg=_target_tolerance_to_core(
                criteria.culmination_azimuth_deg
            ),
            sun_proximity_deg=_range_to_core(criteria.sun_proximity_deg),
            satellite_altitude_km=_range_to_core(criteria.satellite_altitude_km),
            score_threshold=(
                _DISABLED_SCORE_THRESHOLD
                if criteria.score_threshold is None
                else criteria.score_threshold
            ),
            result_limit=(
                _DEFAULT_RESULT_LIMIT
                if criteria.result_limit is None
                else criteria.result_limit
            ),
        ),
        satellite_group=core_models.SatelliteGroup(request.satellite_group),
    )


def core_response_to_api_response(
    response: core_models.SearchResponse,
) -> api_schemas.SearchResponse:
    """Adapt a shared core search response into the public API response schema."""
    return api_schemas.SearchResponse(
        status=response.status.value,
        results=[_candidate_to_api(candidate) for candidate in response.results],
        diagnostics=dict(response.diagnostics),
    )


def _station_to_core(station: api_schemas.SearchStation) -> core_models.GroundStation:
    return core_models.GroundStation(
        latitude=station.latitude,
        longitude=station.longitude,
        elevation_m=station.elevation_m,
    )


def _window_to_core(window: api_schemas.SearchWindow) -> core_models.SearchWindow:
    return core_models.SearchWindow(
        start_at=window.start_at,
        duration_minutes=window.duration_minutes,
    )


def _simple_search_criteria() -> core_models.SearchCriteria:
    return core_models.SearchCriteria(
        culmination_altitude_deg=_range_from_bounds(
            _SIMPLE_CULMINATION_ALTITUDE_DEG
        ),
        start_azimuth_deg=None,
        end_azimuth_deg=None,
        culmination_azimuth_deg=None,
        sun_proximity_deg=_range_from_bounds(_SIMPLE_SUN_PROXIMITY_DEG),
        satellite_altitude_km=_range_from_bounds(_SIMPLE_SATELLITE_ALTITUDE_KM),
        result_limit=_DEFAULT_RESULT_LIMIT,
        score_threshold=_DISABLED_SCORE_THRESHOLD,
    )


def _range_from_bounds(bounds: tuple[float, float]) -> core_models.RangeConstraint:
    return core_models.RangeConstraint(minimum=bounds[0], maximum=bounds[1])


def _range_to_core(
    constraint: api_schemas.RangeConstraint | None,
) -> core_models.RangeConstraint | None:
    if constraint is None:
        return None
    return core_models.RangeConstraint(
        minimum=constraint.minimum,
        maximum=constraint.maximum,
    )


def _target_tolerance_to_core(
    constraint: api_schemas.TargetToleranceConstraint | None,
) -> core_models.TargetToleranceConstraint | None:
    if constraint is None:
        return None
    return core_models.TargetToleranceConstraint(
        target=constraint.target,
        tolerance=constraint.tolerance,
    )


def _candidate_to_api(
    candidate: core_models.CandidatePass,
) -> api_schemas.SearchResultResponse:
    tle = candidate.satellite.tle
    geometry = candidate.geometry
    metrics = candidate.metrics

    return api_schemas.SearchResultResponse(
        rank=candidate.rank,
        match_score=candidate.match_score,
        satellite=api_schemas.SatelliteResponse(
            name=tle.name,
            catalog_number=tle.catalog_number,
            tle=api_schemas.TleResponse(
                name=tle.name,
                line1=tle.line1,
                line2=tle.line2,
                epoch_utc=tle.epoch_utc,
                source_group=tle.source_group.value,
            ),
        ),
        geometry=api_schemas.PassGeometryResponse(
            start_time_utc=geometry.start_time_utc,
            end_time_utc=geometry.end_time_utc,
            culmination_time_utc=geometry.culmination_time_utc,
            start_azimuth_deg=geometry.start_azimuth_deg,
            end_azimuth_deg=geometry.end_azimuth_deg,
            culmination_azimuth_deg=geometry.culmination_azimuth_deg,
            culmination_altitude_deg=geometry.culmination_altitude_deg,
        ),
        metrics=api_schemas.PassMetricsResponse(
            satellite_altitude_km=metrics.satellite_altitude_km,
            sun_proximity_deg=metrics.sun_proximity_deg,
        ),
        diagnostics=dict(candidate.diagnostics),
    )


__all__ = [
    "advanced_search_to_core_request",
    "core_response_to_api_response",
    "simple_search_to_core_request",
]
