"""Single orchestration entrypoint for the reusable core search workflow."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
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
    SearchRequest,
    SearchResponse,
    SearchStatus,
    SearchWindow,
)

NEXT_PASS_WINDOW_MINUTES = 30


def search_candidates(
    request: SearchRequest,
    *,
    cache_dir: Path | str | None = None,
    http_client: tle_repository.HttpClient | None = None,
    source_configs: dict[SatelliteGroup, tle_repository.TleSourceConfig] | None = None,
    max_tle_age_hours: int | None = None,
) -> SearchResponse:
    """Run the full core search workflow and return ranked results."""

    validation.validate_search_request(request)
    interval = time_utils.build_search_interval(request.window)
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
    candidates = pass_analysis.find_candidate_passes(
        records,
        request.station,
        interval,
    )
    filtered_candidates = filtering.filter_candidate_passes(
        candidates,
        request.criteria,
    )
    scored_candidates = [
        scoring.compute_match_score(candidate, request.criteria, interval)
        for candidate in filtered_candidates
    ]
    thresholded_candidates = ranking.apply_score_threshold(
        scored_candidates,
        request.criteria.score_threshold,
    )
    ranked_candidates = ranking.rank_candidates(thresholded_candidates)
    limited_candidates = ranking.limit_results(
        ranked_candidates,
        request.criteria.result_limit,
    )

    diagnostics = {
        "satellite_count": len(records),
        "candidate_count": len(candidates),
        "filtered_count": len(filtered_candidates),
        "thresholded_count": len(thresholded_candidates),
        "returned_count": len(limited_candidates),
    }
    diagnostics.update(_tle_dataset_diagnostics(records))

    return SearchResponse(
        results=limited_candidates,
        status=(
            SearchStatus.RESULTS
            if limited_candidates
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
) -> CandidatePass | None:
    """Return the best-ranked candidate for ``request``, if any."""

    response = search_candidates(
        request,
        **_engine_search_kwargs(
            cache_dir=cache_dir,
            http_client=http_client,
            source_configs=source_configs,
            max_tle_age_hours=max_tle_age_hours,
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
    return kwargs


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


__all__ = [
    "find_best_candidate",
    "find_next_candidate",
    "search_candidates",
]
