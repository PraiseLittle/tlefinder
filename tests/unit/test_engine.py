from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit
FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


def _fixture_config(filename: str):
    from tlefinder.core.models import SatelliteGroup
    from tlefinder.core.tle_repository import TleSourceConfig

    return {
        SatelliteGroup.ACTIVE: TleSourceConfig(
            url="https://example.invalid/active.tle",
            cache_filename=filename,
        )
    }


def _candidate(
    *,
    catalog_number: int = 25544,
    start_offset_minutes: int = 0,
    match_score: float | None = None,
    rank: int | None = None,
):
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        TleRecord,
    )

    epoch = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    start_time = epoch + timedelta(minutes=start_offset_minutes)
    catalog = f"{catalog_number:05d}"
    return CandidatePass(
        satellite=SatelliteRecord(
            tle=TleRecord(
                name=f"SAT-{catalog}",
                line1=f"1 {catalog}U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                line2=f"2 {catalog}  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                catalog_number=catalog_number,
                epoch_utc=epoch,
                source_group=SatelliteGroup.ACTIVE,
                source_path=Path("active.tle"),
            )
        ),
        geometry=PassGeometry(
            start_time_utc=start_time,
            end_time_utc=start_time + timedelta(minutes=5),
            culmination_time_utc=start_time + timedelta(minutes=2, seconds=30),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            culmination_azimuth_deg=180.0,
            culmination_altitude_deg=45.0,
        ),
        metrics=PassMetrics(satellite_altitude_km=420.0, sun_proximity_deg=25.0),
        match_score=match_score,
        rank=rank,
    )


def _request(station_factory, search_window_factory, search_criteria_factory):
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    return SearchRequest(
        station=station_factory(),
        window=search_window_factory(duration_minutes=10),
        criteria=search_criteria_factory(score_threshold=50.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )


def test_search_candidates_orchestrates_the_core_pipeline(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchStatus

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    candidate = _candidate()
    records = [candidate.satellite]
    interval = (
        datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
    )
    calls: list[str] = []

    def validate_search_request(received_request):
        assert received_request is request
        calls.append("validate")

    def build_search_interval(received_window):
        assert received_window is request.window
        calls.append("interval")
        return interval

    def load_tle_dataset(received_group, as_of_utc):
        assert received_group is request.satellite_group
        assert as_of_utc == interval[0]
        calls.append("load")
        return records

    def find_candidate_passes(received_records, received_station, received_interval):
        assert received_records is records
        assert received_station is request.station
        assert received_interval == interval
        calls.append("propagate")
        return [candidate]

    def filter_candidate_passes(received_candidates, received_criteria):
        assert received_candidates == [candidate]
        assert received_criteria is request.criteria
        calls.append("filter")
        return received_candidates

    def compute_match_score(received_candidate, received_criteria, received_interval):
        assert received_candidate is candidate
        assert received_criteria is request.criteria
        assert received_interval == interval
        calls.append("score")
        received_candidate.match_score = 80.0
        return received_candidate

    def apply_score_threshold(received_candidates, threshold):
        assert received_candidates == [candidate]
        assert threshold == 50.0
        calls.append("threshold")
        return received_candidates

    def rank_candidates(received_candidates):
        assert received_candidates == [candidate]
        calls.append("rank")
        candidate.rank = 1
        return received_candidates

    def limit_results(received_candidates, limit):
        assert received_candidates == [candidate]
        assert limit == 2
        calls.append("limit")
        return received_candidates

    monkeypatch.setattr(
        engine.validation,
        "validate_search_request",
        validate_search_request,
    )
    monkeypatch.setattr(engine.time_utils, "build_search_interval", build_search_interval)
    monkeypatch.setattr(engine.tle_repository, "load_tle_dataset", load_tle_dataset)
    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_passes",
        find_candidate_passes,
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_candidate_passes",
        filter_candidate_passes,
    )
    monkeypatch.setattr(engine.scoring, "compute_match_score", compute_match_score)
    monkeypatch.setattr(
        engine.ranking,
        "apply_score_threshold",
        apply_score_threshold,
    )
    monkeypatch.setattr(engine.ranking, "rank_candidates", rank_candidates)
    monkeypatch.setattr(engine.ranking, "limit_results", limit_results)

    response = engine.search_candidates(request)

    assert calls == [
        "validate",
        "interval",
        "load",
        "propagate",
        "filter",
        "score",
        "threshold",
        "rank",
        "limit",
    ]
    assert response.status is SearchStatus.RESULTS
    assert response.results == [candidate]
    assert response.diagnostics == {
        "satellite_count": 1,
        "candidate_count": 1,
        "filtered_count": 1,
        "thresholded_count": 1,
        "returned_count": 1,
    }


def test_search_candidates_returns_no_result_as_normal_status(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchStatus

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    candidate = _candidate()

    monkeypatch.setattr(engine.validation, "validate_search_request", lambda request: None)
    monkeypatch.setattr(
        engine.time_utils,
        "build_search_interval",
        lambda window: (
            datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_passes",
        lambda records, station, interval: [candidate],
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_candidate_passes",
        lambda candidates, criteria: [],
    )

    response = engine.search_candidates(request)

    assert response.status is SearchStatus.NO_RESULT
    assert response.results == []
    assert response.diagnostics["candidate_count"] == 1
    assert response.diagnostics["filtered_count"] == 0


def test_search_candidates_rejects_invalid_satellite_group_before_loading_or_propagation(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.models import SearchRequest

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group="active",
    )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda *args, **kwargs: pytest.fail("TLE loading must not start"),
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_passes",
        lambda *args, **kwargs: pytest.fail("propagation must not start"),
    )

    with pytest.raises(ValidationError, match="satellite_group"):
        engine.search_candidates(request)


def test_search_candidates_passes_requested_satellite_group_to_repository(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchRequest, SearchStatus

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(duration_minutes=10),
        criteria=search_criteria_factory(),
        satellite_group=SatelliteGroup.VISUAL,
    )
    candidate = _candidate()
    candidate.satellite.tle.source_group = SatelliteGroup.VISUAL
    candidate.satellite.metadata["source_group"] = SatelliteGroup.VISUAL.value
    received_groups: list[SatelliteGroup] = []

    def load_tle_dataset(group, as_of_utc):
        received_groups.append(group)
        return [candidate.satellite]

    monkeypatch.setattr(engine.tle_repository, "load_tle_dataset", load_tle_dataset)
    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_passes",
        lambda records, station, interval: [candidate],
    )

    response = engine.search_candidates(request)

    assert response.status is SearchStatus.RESULTS
    assert received_groups == [SatelliteGroup.VISUAL]


def test_search_candidates_can_return_results_from_mixed_age_tle_source(
    monkeypatch,
    tmp_path,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchRequest, SearchStatus

    cached_path = tmp_path / "active.tle"
    cached_path.write_text(
        (FIXTURES_DIR / "active_sample.tle").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(
            start_at=datetime(2026, 5, 13, 11, 0, tzinfo=timezone.utc),
            duration_minutes=10,
        ),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=5),
        satellite_group=engine.tle_repository.SatelliteGroup.ACTIVE,
    )

    class OfflineClient:
        def get(self, url):
            raise AssertionError("mixed fresh cache should avoid network retrieval")

    def find_candidate_passes(records, station, interval):
        assert [record.tle.name for record in records] == ["ISS (ZARYA)"]
        candidate = _candidate(catalog_number=records[0].tle.catalog_number)
        candidate.satellite = records[0]
        return [candidate]

    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_passes",
        find_candidate_passes,
    )

    response = engine.search_candidates(
        request,
        cache_dir=tmp_path,
        http_client=OfflineClient(),
        source_configs=_fixture_config("active.tle"),
    )

    assert response.status is SearchStatus.RESULTS
    assert [candidate.satellite.tle.name for candidate in response.results] == [
        "ISS (ZARYA)"
    ]
    assert response.diagnostics["satellite_count"] == 1
    assert response.diagnostics["fresh_tle_record_count"] == 1
    assert response.diagnostics["stale_tle_record_count"] == 1


def test_find_best_candidate_returns_first_ranked_result(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchResponse, SearchStatus

    best = _candidate(catalog_number=1, match_score=95.0, rank=1)
    second = _candidate(catalog_number=2, match_score=90.0, rank=2)
    monkeypatch.setattr(
        engine,
        "search_candidates",
        lambda request: SearchResponse(
            results=[best, second],
            status=SearchStatus.RESULTS,
        ),
    )

    assert (
        engine.find_best_candidate(
            _request(station_factory, search_window_factory, search_criteria_factory)
        )
        is best
    )


def test_find_best_candidate_returns_none_for_no_result(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchResponse, SearchStatus

    monkeypatch.setattr(
        engine,
        "search_candidates",
        lambda request: SearchResponse(results=[], status=SearchStatus.NO_RESULT),
    )

    assert (
        engine.find_best_candidate(
            _request(station_factory, search_window_factory, search_criteria_factory)
        )
        is None
    )


def test_find_next_candidate_scans_forward_with_thirty_minute_windows(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SearchResponse, SearchStatus

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    best = _candidate(catalog_number=1, match_score=95.0, rank=1)
    calls: list[tuple[datetime, float, dict[str, object]]] = []
    cache_dir = Path("local-cache")

    def search_candidates(received_request, **kwargs):
        calls.append(
            (
                received_request.window.start_at,
                received_request.window.duration_minutes,
                kwargs,
            )
        )
        if len(calls) == 2:
            return SearchResponse(results=[best], status=SearchStatus.RESULTS)
        return SearchResponse(results=[], status=SearchStatus.NO_RESULT)

    monkeypatch.setattr(engine, "search_candidates", search_candidates)

    result = engine.find_next_candidate(request, max_windows=3, cache_dir=cache_dir)

    assert result is best
    assert calls == [
        (
            datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
            30,
            {"cache_dir": cache_dir},
        ),
        (
            datetime(2026, 5, 12, 20, 30, tzinfo=timezone.utc),
            30,
            {"cache_dir": cache_dir},
        ),
    ]


def test_core_package_exports_engine_entrypoints():
    from tlefinder.core import find_best_candidate, find_next_candidate, search_candidates

    assert callable(search_candidates)
    assert callable(find_best_candidate)
    assert callable(find_next_candidate)
