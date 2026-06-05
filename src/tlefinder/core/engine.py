"""Single orchestration entrypoint for the reusable core search workflow."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from math import isfinite
from pathlib import Path
import time
from typing import Any

import tlefinder.core.filtering as filtering
import tlefinder.core.pass_analysis as pass_analysis
import tlefinder.core.ranking as ranking
import tlefinder.core.scoring as scoring
import tlefinder.core.time_utils as time_utils
import tlefinder.core.tle_repository as tle_repository
import tlefinder.core.validation as validation
from tlefinder.core.models import (
    CandidatePass,
    SatelliteGroup,
    SatelliteRecord,
    SearchCriteria,
    SearchRequest,
    SearchResponse,
    SearchStatus,
    SearchWindow,
)

NEXT_PASS_WINDOW_MINUTES = 30
CANDIDATE_BUDGET_MULTIPLIER = 6
APPROXIMATE_BUDGET_NOTE = (
    "Budgeted results are approximate because unseen satellites might have scored higher."
)
_RANGE_TOLERANCE = 1e-9
_APPARENT_ALTITUDE_DOMAIN_DEG = (0.0, 90.0)
_SUN_PROXIMITY_DOMAIN_DEG = (0.0, 180.0)
_BUDGET_COMPATIBLE_SATELLITE_ALTITUDE_KM = (200.0, 2000.0)


@dataclass(frozen=True, slots=True)
class _CandidateBudgetPolicy:
    requested: bool
    enabled: bool
    candidate_budget: int | None
    disabled_reason: str | None = None


def search_candidates(
    request: SearchRequest,
    *,
    cache_dir: Path | str | None = None,
    http_client: tle_repository.HttpClient | None = None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None = None,
    max_tle_age_hours: int | None = None,
    timer: Callable[[], float] | None = None,
    approximate_budgeted: bool = False,
    parallel_search: pass_analysis.ParallelSearchConfig | None = None,
) -> SearchResponse:
    """Run the full core search workflow and return ranked results."""

    timer_func = time.perf_counter if timer is None else timer
    timings_ms: dict[str, float] = {}
    total_start = _read_timer(timer_func)

    with _record_stage_timing(timings_ms, "validation", timer_func):
        validation.validate_search_request(request)
    budget_policy = _candidate_budget_policy(
        request,
        approximate_budgeted=approximate_budgeted,
        parallel_search=parallel_search,
    )
    with _record_stage_timing(timings_ms, "interval_normalization", timer_func):
        interval = time_utils.build_search_interval(request.window)
    with _record_stage_timing(timings_ms, "tle_loading", timer_func):
        records = tle_repository.load_tle_dataset(
            request.satellite_group,
            interval[0],
            **_tle_repository_kwargs(
                cache_dir=cache_dir,
                http_client=http_client,
                source_configs=source_configs,
                max_tle_age_hours=max_tle_age_hours,
            ),
        )
    with _record_stage_timing(timings_ms, "pass_analysis", timer_func):
        pass_analysis_session = pass_analysis.create_pass_analysis_session(
            request.station,
            interval,
        )
        pass_analysis_result = _find_candidate_geometries_with_diagnostics(
            pass_analysis_session,
            records,
            station=request.station,
            interval=interval,
            candidate_budget=budget_policy.candidate_budget,
            parallel_search=parallel_search,
        )
        candidates = pass_analysis_result.candidates
    with _record_stage_timing(timings_ms, "geometry_filtering", timer_func):
        geometry_filtered_candidates = filtering.filter_geometry_candidate_passes(
            candidates,
            request.criteria,
        )
    with _record_stage_timing(timings_ms, "metric_computation", timer_func):
        metric_ready_candidates = pass_analysis_session.compute_required_metrics(
            geometry_filtered_candidates,
            include_satellite_altitude=_requires_satellite_altitude_filter(
                request.criteria
            ),
            include_sun_proximity=_requires_sun_proximity_metric(request.criteria),
        )
    with _record_stage_timing(timings_ms, "metric_filtering", timer_func):
        filtered_candidates = filtering.filter_metric_candidate_passes(
            metric_ready_candidates,
            request.criteria,
        )
    with _record_stage_timing(timings_ms, "scoring", timer_func):
        scored_candidates = [
            scoring.compute_match_score(candidate, request.criteria, interval)
            for candidate in filtered_candidates
        ]
    with _record_stage_timing(timings_ms, "thresholding", timer_func):
        thresholded_candidates = ranking.apply_score_threshold(
            scored_candidates,
            request.criteria.score_threshold,
        )
    with _record_stage_timing(timings_ms, "ranking", timer_func):
        ranked_candidates = ranking.rank_candidates(thresholded_candidates)
    with _record_stage_timing(timings_ms, "limiting", timer_func):
        limited_candidates = ranking.limit_results(
            ranked_candidates,
            request.criteria.result_limit,
        )
    with _record_stage_timing(timings_ms, "response_metric_completion", timer_func):
        pass_analysis_session.compute_required_metrics(
            _metric_completion_order(limited_candidates),
            include_satellite_altitude=True,
            include_sun_proximity=True,
        )
        response_candidates = limited_candidates
    _record_elapsed(timings_ms, "total", total_start, _read_timer(timer_func))
    budget_diagnostics = _candidate_budget_diagnostics(
        budget_policy,
        pass_analysis_result.diagnostics,
        satellite_count=len(records),
        processed_candidate_count=len(candidates),
        returned_candidate_count=len(response_candidates),
    )

    diagnostics = {
        "satellite_count": len(records),
        "candidate_count": len(candidates),
        "geometry_filtered_count": len(geometry_filtered_candidates),
        "filtered_count": len(filtered_candidates),
        "thresholded_count": len(thresholded_candidates),
        "returned_count": len(response_candidates),
        "timings_ms": timings_ms,
        "pass_analysis": dict(pass_analysis_result.diagnostics),
        "search_optimization": _search_optimization_diagnostics(
            budget_diagnostics,
        ),
        "candidate_budget": budget_diagnostics,
    }
    parallel_diagnostics = _parallel_search_diagnostics(
        pass_analysis_result.diagnostics,
    )
    if parallel_diagnostics is not None:
        diagnostics["parallel_search"] = parallel_diagnostics
    diagnostics.update(_tle_dataset_diagnostics(records))

    return SearchResponse(
        results=response_candidates,
        status=(
            SearchStatus.RESULTS
            if response_candidates
            else SearchStatus.NO_RESULT
        ),
        diagnostics=diagnostics,
    )


def find_best_candidate(
    request: SearchRequest,
    *,
    cache_dir: Path | str | None = None,
    http_client: tle_repository.HttpClient | None = None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None = None,
    max_tle_age_hours: int | None = None,
    timer: Callable[[], float] | None = None,
    approximate_budgeted: bool = False,
    parallel_search: pass_analysis.ParallelSearchConfig | None = None,
) -> CandidatePass | None:
    """Return the best-ranked candidate for ``request``, if any."""

    response = search_candidates(
        request,
        **_engine_search_kwargs(
            cache_dir=cache_dir,
            http_client=http_client,
            source_configs=source_configs,
            max_tle_age_hours=max_tle_age_hours,
            timer=timer,
            approximate_budgeted=approximate_budgeted,
            parallel_search=parallel_search,
        ),
    )
    if not response.results:
        return None
    return response.results[0]


def find_next_candidate(
    request: SearchRequest,
    *,
    max_windows: int = 48,
    cache_dir: Path | str | None = None,
    http_client: tle_repository.HttpClient | None = None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None = None,
    max_tle_age_hours: int | None = None,
    timer: Callable[[], float] | None = None,
    approximate_budgeted: bool = False,
    parallel_search: pass_analysis.ParallelSearchConfig | None = None,
) -> CandidatePass | None:
    """Scan forward in 30-minute windows and return the first best candidate.

    Ongoing visible passes at a window start count as results because pass
    analysis accepts passes that overlap the requested interval.
    """

    if max_windows <= 0:
        return None

    search_kwargs = _engine_search_kwargs(
        cache_dir=cache_dir,
        http_client=http_client,
        source_configs=source_configs,
        max_tle_age_hours=max_tle_age_hours,
        timer=timer,
        approximate_budgeted=approximate_budgeted,
        parallel_search=parallel_search,
    )
    for offset in range(max_windows):
        window = SearchWindow(
            start_at=request.window.start_at
            + timedelta(minutes=NEXT_PASS_WINDOW_MINUTES * offset),
            duration_minutes=NEXT_PASS_WINDOW_MINUTES,
        )
        window_request = replace(request, window=window)
        response = search_candidates(window_request, **search_kwargs)
        if response.results:
            return response.results[0]

    return None


def _tle_repository_kwargs(
    *,
    cache_dir: Path | str | None,
    http_client: tle_repository.HttpClient | None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None,
    max_tle_age_hours: int | None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    if http_client is not None:
        kwargs["http_client"] = http_client
    if source_configs is not None:
        kwargs["source_configs"] = source_configs
    if max_tle_age_hours is not None:
        kwargs["max_age_hours"] = max_tle_age_hours
    return kwargs


def _engine_search_kwargs(
    *,
    cache_dir: Path | str | None,
    http_client: tle_repository.HttpClient | None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None,
    max_tle_age_hours: int | None,
    timer: Callable[[], float] | None = None,
    approximate_budgeted: bool = False,
    parallel_search: pass_analysis.ParallelSearchConfig | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    if http_client is not None:
        kwargs["http_client"] = http_client
    if source_configs is not None:
        kwargs["source_configs"] = source_configs
    if max_tle_age_hours is not None:
        kwargs["max_tle_age_hours"] = max_tle_age_hours
    if timer is not None:
        kwargs["timer"] = timer
    if approximate_budgeted:
        kwargs["approximate_budgeted"] = approximate_budgeted
    if parallel_search is not None:
        kwargs["parallel_search"] = parallel_search
    return kwargs


def _candidate_budget_policy(
    request: SearchRequest,
    *,
    approximate_budgeted: bool,
    parallel_search: pass_analysis.ParallelSearchConfig | None = None,
) -> _CandidateBudgetPolicy:
    if not approximate_budgeted:
        return _CandidateBudgetPolicy(
            requested=False,
            enabled=False,
            candidate_budget=None,
        )
    if request.satellite_group != SatelliteGroup.ACTIVE:
        return _CandidateBudgetPolicy(
            requested=True,
            enabled=False,
            candidate_budget=None,
            disabled_reason="satellite_group",
        )
    if _has_strict_hard_filters(request.criteria):
        return _CandidateBudgetPolicy(
            requested=True,
            enabled=False,
            candidate_budget=None,
            disabled_reason="strict_filters",
        )
    return _CandidateBudgetPolicy(
        requested=True,
        enabled=True,
        candidate_budget=request.criteria.result_limit * CANDIDATE_BUDGET_MULTIPLIER,
    )


def _has_strict_hard_filters(criteria: SearchCriteria) -> bool:
    if any(
        criterion is not None
        for criterion in (
            criteria.culmination_altitude_target_deg,
            criteria.start_azimuth_deg,
            criteria.end_azimuth_deg,
            criteria.culmination_azimuth_deg,
        )
    ):
        return True

    return any(
        (
            _is_strict_range_filter(
                criteria.culmination_altitude_deg,
                domain=_APPARENT_ALTITUDE_DOMAIN_DEG,
            ),
            _is_strict_range_filter(
                criteria.sun_proximity_deg,
                domain=_SUN_PROXIMITY_DOMAIN_DEG,
            ),
            _is_strict_satellite_altitude_filter(criteria.satellite_altitude_km),
        )
    )


def _is_strict_satellite_altitude_filter(
    constraint: Any,
) -> bool:
    if constraint is None:
        return False
    if _range_covers(
        constraint,
        lower=_BUDGET_COMPATIBLE_SATELLITE_ALTITUDE_KM[0],
        upper=_BUDGET_COMPATIBLE_SATELLITE_ALTITUDE_KM[1],
    ):
        return False
    return True


def _is_strict_range_filter(
    constraint: Any,
    *,
    domain: tuple[float, float],
) -> bool:
    if constraint is None:
        return False
    return not _range_covers(constraint, lower=domain[0], upper=domain[1])


def _range_covers(
    constraint: Any,
    *,
    lower: float,
    upper: float,
) -> bool:
    minimum = constraint.minimum
    maximum = constraint.maximum
    minimum_covers = minimum is None or minimum <= lower + _RANGE_TOLERANCE
    maximum_covers = maximum is None or maximum >= upper - _RANGE_TOLERANCE
    return minimum_covers and maximum_covers


def _find_candidate_geometries_with_diagnostics(
    pass_analysis_session: Any,
    records: list[SatelliteRecord],
    *,
    station: Any,
    interval: tuple[Any, Any],
    candidate_budget: int | None,
    parallel_search: pass_analysis.ParallelSearchConfig | None,
) -> pass_analysis.PassAnalysisResult:
    if parallel_search is not None and parallel_search.enabled:
        kwargs: dict[str, Any] = {"parallel_search": parallel_search}
        if candidate_budget is not None:
            kwargs["candidate_budget"] = candidate_budget
        return pass_analysis.find_candidate_geometries_with_diagnostics(
            records,
            station,
            interval,
            **kwargs,
        )

    kwargs = {}
    if candidate_budget is None:
        if parallel_search is not None:
            kwargs["parallel_search"] = parallel_search
        return pass_analysis_session.find_candidate_geometries_with_diagnostics(
            records,
            **kwargs,
        )
    kwargs["candidate_budget"] = candidate_budget
    if parallel_search is not None:
        kwargs["parallel_search"] = parallel_search
    return pass_analysis_session.find_candidate_geometries_with_diagnostics(
        records,
        **kwargs,
    )


def _parallel_search_diagnostics(
    pass_analysis_diagnostics: dict[str, Any],
) -> dict[str, Any] | None:
    diagnostics = pass_analysis_diagnostics.get("parallel_search")
    if not isinstance(diagnostics, dict):
        return None
    return dict(diagnostics)


def _requires_satellite_altitude_filter(criteria: SearchCriteria) -> bool:
    return criteria.satellite_altitude_km is not None


def _requires_sun_proximity_metric(criteria: SearchCriteria) -> bool:
    return criteria.sun_proximity_deg is not None


def _exact_optimization_diagnostics() -> dict[str, Any]:
    return {
        "mode": "exact_geometry_first_deferred_metrics",
        "approximate_budgeting": False,
        "geometry_first_filtering": True,
        "deferred_metrics": True,
    }


def _search_optimization_diagnostics(
    budget_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    if not budget_diagnostics["enabled"]:
        return _exact_optimization_diagnostics()
    return {
        "mode": "approximate_budgeted_geometry_first_deferred_metrics",
        "approximate_budgeting": True,
        "geometry_first_filtering": True,
        "deferred_metrics": True,
        "candidate_budget": budget_diagnostics["candidate_budget"],
        "budget_reached": budget_diagnostics["budget_reached"],
        "approximate": budget_diagnostics["approximate"],
    }


def _candidate_budget_diagnostics(
    policy: _CandidateBudgetPolicy,
    pass_analysis_diagnostics: dict[str, Any],
    *,
    satellite_count: int,
    processed_candidate_count: int,
    returned_candidate_count: int,
) -> dict[str, Any]:
    processed_satellite_count = _diagnostic_int(
        pass_analysis_diagnostics,
        "processed_satellite_count",
        default=_diagnostic_int(
            pass_analysis_diagnostics,
            "satellite_records_inspected",
            default=satellite_count,
        ),
    )
    unprocessed_satellite_count = _diagnostic_int(
        pass_analysis_diagnostics,
        "unprocessed_satellite_count",
        default=max(0, satellite_count - processed_satellite_count),
    )
    budget_reached = bool(pass_analysis_diagnostics.get("budget_reached", False))
    approximate = bool(policy.enabled and budget_reached)

    return {
        "requested": policy.requested,
        "enabled": policy.enabled,
        "disabled_reason": policy.disabled_reason,
        "candidate_budget": policy.candidate_budget,
        "budget_reached": budget_reached,
        "processed_satellite_count": processed_satellite_count,
        "unprocessed_satellite_count": unprocessed_satellite_count,
        "processed_candidate_count": _diagnostic_int(
            pass_analysis_diagnostics,
            "processed_candidate_count",
            default=processed_candidate_count,
        ),
        "returned_candidate_count": returned_candidate_count,
        "approximate": approximate,
        "approximation_note": APPROXIMATE_BUDGET_NOTE if approximate else None,
    }


def _diagnostic_int(
    diagnostics: dict[str, Any],
    key: str,
    *,
    default: int,
) -> int:
    value = diagnostics.get(key, default)
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _metric_completion_order(
    candidates: list[CandidatePass],
) -> list[CandidatePass]:
    return sorted(
        candidates,
        key=lambda candidate: candidate.satellite.tle.catalog_number,
    )


def _tle_dataset_diagnostics(records: list[SatelliteRecord]) -> dict[str, Any]:
    if not records:
        return {}

    dataset_metadata = records[0].metadata.get("tle_dataset")
    if not isinstance(dataset_metadata, dict):
        return {}

    return {
        "tle_record_count": dataset_metadata.get("total_record_count"),
        "fresh_tle_record_count": dataset_metadata.get("fresh_record_count"),
        "stale_tle_record_count": dataset_metadata.get("stale_record_count"),
        "tle_max_age_hours": dataset_metadata.get("max_age_hours"),
    }


@contextmanager
def _record_stage_timing(
    timings_ms: dict[str, float],
    stage_name: str,
    timer: Callable[[], float],
) -> Iterator[None]:
    start = _read_timer(timer)
    try:
        yield
    finally:
        _record_elapsed(timings_ms, stage_name, start, _read_timer(timer))


def _record_elapsed(
    timings_ms: dict[str, float],
    stage_name: str,
    start: float | None,
    end: float | None,
) -> None:
    if start is None or end is None:
        return
    timings_ms[stage_name] = round(max(0.0, end - start) * 1000.0, 6)


def _read_timer(timer: Callable[[], float]) -> float | None:
    try:
        value = float(timer())
    except Exception:
        return None
    if not isfinite(value):
        return None
    return value


__all__ = [
    "find_best_candidate",
    "find_next_candidate",
    "search_candidates",
]
