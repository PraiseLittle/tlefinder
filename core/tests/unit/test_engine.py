from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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
    culmination_altitude_deg: float = 45.0,
    start_azimuth_deg: float = 270.0,
    end_azimuth_deg: float = 90.0,
    culmination_azimuth_deg: float = 180.0,
    satellite_altitude_km: float | None = 420.0,
    sun_proximity_deg: float | None = 25.0,
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
            start_azimuth_deg=start_azimuth_deg,
            end_azimuth_deg=end_azimuth_deg,
            culmination_azimuth_deg=culmination_azimuth_deg,
            culmination_altitude_deg=culmination_altitude_deg,
        ),
        metrics=PassMetrics(
            satellite_altitude_km=satellite_altitude_km,
            sun_proximity_deg=sun_proximity_deg,
        ),
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


def _pass_analysis_result(candidates, diagnostics: dict[str, Any] | None = None):
    from tlefinder.core.pass_analysis import PassAnalysisResult

    return PassAnalysisResult(
        candidates=list(candidates),
        diagnostics=diagnostics
        or {
            "satellite_records_inspected": len(candidates),
            "candidate_geometries_found": len(candidates),
            "skipped_record_count": 0,
            "skipped_records": [],
            "event_search_span": {
                "start_utc": "2026-05-12T00:00:00Z",
                "end_utc": "2026-05-14T00:00:00Z",
            },
        },
    )


class DeterministicTimer:
    def __init__(self, *, step_seconds: float = 0.001):
        self._value = 0.0
        self._step_seconds = step_seconds

    def __call__(self) -> float:
        value = self._value
        self._value += self._step_seconds
        return value


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

    class FakePassAnalysisSession:
        def find_candidate_geometries_with_diagnostics(self, received_records):
            assert received_records is records
            calls.append("propagate_geometry")
            return _pass_analysis_result([candidate])

        def compute_required_metrics(
            self,
            received_candidates,
            *,
            include_satellite_altitude,
            include_sun_proximity,
        ):
            assert received_candidates == [candidate]
            if include_satellite_altitude and include_sun_proximity:
                calls.append("complete_response_metrics")
            else:
                assert not include_satellite_altitude
                assert not include_sun_proximity
                calls.append("compute_filter_metrics")
            return received_candidates

    def create_pass_analysis_session(
        received_station,
        received_interval,
    ):
        assert received_station is request.station
        assert received_interval == interval
        calls.append("create_pass_analysis")
        return FakePassAnalysisSession()

    def filter_geometry_candidate_passes(received_candidates, received_criteria):
        assert received_candidates == [candidate]
        assert received_criteria is request.criteria
        calls.append("filter_geometry")
        return received_candidates

    def filter_metric_candidate_passes(received_candidates, received_criteria):
        assert received_candidates == [candidate]
        assert received_criteria is request.criteria
        calls.append("filter_metrics")
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
        "create_pass_analysis_session",
        create_pass_analysis_session,
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_geometry_candidate_passes",
        filter_geometry_candidate_passes,
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_metric_candidate_passes",
        filter_metric_candidate_passes,
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
        "create_pass_analysis",
        "propagate_geometry",
        "filter_geometry",
        "compute_filter_metrics",
        "filter_metrics",
        "score",
        "threshold",
        "rank",
        "limit",
        "complete_response_metrics",
    ]
    assert response.status is SearchStatus.RESULTS
    assert response.results == [candidate]
    assert response.diagnostics["satellite_count"] == 1
    assert response.diagnostics["candidate_count"] == 1
    assert response.diagnostics["filtered_count"] == 1
    assert response.diagnostics["geometry_filtered_count"] == 1
    assert response.diagnostics["thresholded_count"] == 1
    assert response.diagnostics["returned_count"] == 1
    assert response.diagnostics["search_optimization"] == {
        "mode": "exact_geometry_first_deferred_metrics",
        "approximate_budgeting": False,
        "geometry_first_filtering": True,
        "deferred_metrics": True,
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
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession([candidate]),
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_geometry_candidate_passes",
        lambda candidates, criteria: [],
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_metric_candidate_passes",
        lambda candidates, criteria: candidates,
    )

    response = engine.search_candidates(request)

    assert response.status is SearchStatus.NO_RESULT
    assert response.results == []
    assert response.diagnostics["candidate_count"] == 1
    assert response.diagnostics["filtered_count"] == 0
    assert response.diagnostics["geometry_filtered_count"] == 0


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
        "create_pass_analysis_session",
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
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession([candidate]),
    )

    response = engine.search_candidates(request)

    assert response.status is SearchStatus.RESULTS
    assert received_groups == [SatelliteGroup.VISUAL]


def test_search_candidates_omits_default_tle_age_limit_repository_kwarg(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    candidate = _candidate()
    received_kwargs: list[dict[str, Any]] = []

    def load_tle_dataset(group, as_of_utc, **kwargs):
        received_kwargs.append(kwargs)
        return [candidate.satellite]

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(duration_minutes=10),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=1),
        satellite_group=SatelliteGroup.ACTIVE,
    )

    monkeypatch.setattr(engine.tle_repository, "load_tle_dataset", load_tle_dataset)
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession([candidate]),
    )

    engine.search_candidates(request)

    assert received_kwargs == [{}]


def test_search_candidates_maps_one_week_tle_age_limit_to_repository_max_age(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchRequest, TleAgeLimit

    candidate = _candidate()
    received_kwargs: list[dict[str, Any]] = []

    def load_tle_dataset(group, as_of_utc, **kwargs):
        received_kwargs.append(kwargs)
        return [candidate.satellite]

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(duration_minutes=10),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=1),
        satellite_group=SatelliteGroup.ACTIVE,
        tle_age_limit=TleAgeLimit.WEEK_1,
    )

    monkeypatch.setattr(engine.tle_repository, "load_tle_dataset", load_tle_dataset)
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession([candidate]),
    )

    engine.search_candidates(request)

    assert received_kwargs == [{"max_age_hours": engine.TLE_ONE_WEEK_MAX_AGE_HOURS}]


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

    class MixedAgePassAnalysisSession:
        def find_candidate_geometries_with_diagnostics(self, records):
            assert [record.tle.name for record in records] == ["ISS (ZARYA)"]
            candidate = _candidate(catalog_number=records[0].tle.catalog_number)
            candidate.satellite = records[0]
            return _pass_analysis_result(
                [candidate],
                {
                    "satellite_records_inspected": 1,
                    "candidate_geometries_found": 1,
                    "skipped_record_count": 0,
                    "skipped_records": [],
                    "event_search_span": {
                        "start_utc": "2026-05-13T00:00:00Z",
                        "end_utc": "2026-05-15T00:00:00Z",
                    },
                },
            )

        def compute_required_metrics(
            self,
            candidates,
            *,
            include_satellite_altitude,
            include_sun_proximity,
        ):
            return candidates

    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: MixedAgePassAnalysisSession(),
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


def test_search_candidates_preserves_count_diagnostics_with_pass_analysis_work(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    first = _candidate(catalog_number=1)
    second = _candidate(catalog_number=2)
    records = [first.satellite, second.satellite]

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
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession(
            [first, second],
            diagnostics={
                "satellite_records_inspected": 2,
                "candidate_geometries_found": 2,
                "skipped_record_count": 0,
                "skipped_records": [],
                "event_search_span": {
                    "start_utc": "2026-05-12T00:00:00Z",
                    "end_utc": "2026-05-14T00:00:00Z",
                },
            },
        ),
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_geometry_candidate_passes",
        lambda candidates, criteria: [first],
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_metric_candidate_passes",
        lambda candidates, criteria: candidates,
    )
    monkeypatch.setattr(
        engine.scoring,
        "compute_match_score",
        lambda candidate, criteria, interval: _set_score(candidate, 80.0),
    )
    monkeypatch.setattr(
        engine.ranking,
        "apply_score_threshold",
        lambda candidates, threshold: candidates,
    )
    monkeypatch.setattr(
        engine.ranking,
        "rank_candidates",
        lambda candidates: [_set_rank(candidate, index) for index, candidate in enumerate(candidates, start=1)],
    )
    monkeypatch.setattr(
        engine.ranking,
        "limit_results",
        lambda candidates, limit: candidates,
    )

    response = engine.search_candidates(request, timer=DeterministicTimer())

    assert response.diagnostics["satellite_count"] == 2
    assert response.diagnostics["candidate_count"] == 2
    assert response.diagnostics["geometry_filtered_count"] == 1
    assert response.diagnostics["filtered_count"] == 1
    assert response.diagnostics["thresholded_count"] == 1
    assert response.diagnostics["returned_count"] == 1
    assert response.diagnostics["pass_analysis"] == {
        "satellite_records_inspected": 2,
        "candidate_geometries_found": 2,
        "skipped_record_count": 0,
        "skipped_records": [],
        "event_search_span": {
            "start_utc": "2026-05-12T00:00:00Z",
            "end_utc": "2026-05-14T00:00:00Z",
        },
    }


def test_exact_optimized_pipeline_matches_legacy_filter_score_rank_results(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine, filtering, ranking, scoring
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
        TargetToleranceConstraint,
    )

    interval = (
        datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
    )
    criteria = SearchCriteria(
        culmination_altitude_deg=RangeConstraint(minimum=30.0, maximum=70.0),
        start_azimuth_deg=TargetToleranceConstraint(target=270.0, tolerance=20.0),
        sun_proximity_deg=RangeConstraint(minimum=10.0, maximum=30.0),
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0),
        score_threshold=0.0,
        result_limit=2,
    )
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(start_at=interval[0], duration_minutes=10),
        criteria=criteria,
        satellite_group=SatelliteGroup.ACTIVE,
    )
    optimized_candidates = [
        _candidate(catalog_number=1, satellite_altitude_km=None, sun_proximity_deg=None),
        _candidate(
            catalog_number=2,
            start_offset_minutes=1,
            culmination_altitude_deg=60.0,
            satellite_altitude_km=None,
            sun_proximity_deg=None,
        ),
        _candidate(
            catalog_number=3,
            culmination_altitude_deg=10.0,
            satellite_altitude_km=None,
            sun_proximity_deg=None,
        ),
        _candidate(
            catalog_number=4,
            satellite_altitude_km=None,
            sun_proximity_deg=None,
        ),
    ]
    metric_values = {
        1: (420.0, 25.0),
        2: (430.0, 20.0),
        3: (420.0, 20.0),
        4: (420.0, 50.0),
    }
    full_candidates = [
        _candidate(catalog_number=1, satellite_altitude_km=420.0, sun_proximity_deg=25.0),
        _candidate(
            catalog_number=2,
            start_offset_minutes=1,
            culmination_altitude_deg=60.0,
            satellite_altitude_km=430.0,
            sun_proximity_deg=20.0,
        ),
        _candidate(
            catalog_number=3,
            culmination_altitude_deg=10.0,
            satellite_altitude_km=420.0,
            sun_proximity_deg=20.0,
        ),
        _candidate(catalog_number=4, satellite_altitude_km=420.0, sun_proximity_deg=50.0),
    ]
    expected = ranking.limit_results(
        ranking.rank_candidates(
            ranking.apply_score_threshold(
                [
                    scoring.compute_match_score(candidate, criteria, interval)
                    for candidate in filtering.filter_candidate_passes(
                        full_candidates,
                        criteria,
                    )
                ],
                criteria.score_threshold,
            )
        ),
        criteria.result_limit,
    )
    metric_calls: list[tuple[list[int], bool, bool]] = []
    session = _FakePassAnalysisSession(
        optimized_candidates,
        diagnostics={
            "satellite_records_inspected": 4,
            "candidate_geometries_found": 4,
            "skipped_record_count": 0,
            "skipped_records": [],
            "event_search_span": {
                "start_utc": "2026-05-12T20:00:00Z",
                "end_utc": "2026-05-12T20:10:00Z",
            },
        },
        metric_values=metric_values,
        metric_calls=metric_calls,
    )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite for candidate in optimized_candidates],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: session,
    )

    response = engine.search_candidates(request)

    assert _result_signature(response.results) == _result_signature(expected)
    assert response.diagnostics["satellite_count"] == 4
    assert response.diagnostics["candidate_count"] == 4
    assert response.diagnostics["geometry_filtered_count"] == 3
    assert response.diagnostics["filtered_count"] == 2
    assert response.diagnostics["returned_count"] == 2
    assert response.diagnostics["pass_analysis"]["satellite_records_inspected"] == 4
    assert metric_calls[0] == ([1, 2, 4], True, True)
    assert metric_calls[-1] == ([1, 2], True, True)


def test_geometry_first_filtering_skips_metric_computation_for_rejected_candidates(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
    )

    accepted = _candidate(
        catalog_number=1,
        culmination_altitude_deg=50.0,
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    geometry_rejected = _candidate(
        catalog_number=2,
        culmination_altitude_deg=20.0,
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    criteria = SearchCriteria(
        culmination_altitude_deg=RangeConstraint(minimum=30.0, maximum=70.0),
        sun_proximity_deg=RangeConstraint(minimum=15.0, maximum=30.0),
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0),
        score_threshold=0.0,
        result_limit=5,
    )
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=criteria,
        satellite_group=SatelliteGroup.ACTIVE,
    )
    metric_calls: list[tuple[list[int], bool, bool]] = []
    session = _FakePassAnalysisSession(
        [accepted, geometry_rejected],
        metric_calls=metric_calls,
    )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [accepted.satellite, geometry_rejected.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: session,
    )

    response = engine.search_candidates(request)

    assert [candidate.satellite.tle.catalog_number for candidate in response.results] == [1]
    assert metric_calls[0] == ([1], True, True)
    assert geometry_rejected.diagnostics["rejection_reasons"] == [
        "culmination_altitude"
    ]


def test_metric_dependent_filters_run_after_deferred_metrics_are_populated(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
    )

    accepted = _candidate(
        catalog_number=1,
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    metric_rejected = _candidate(
        catalog_number=2,
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    criteria = SearchCriteria(
        sun_proximity_deg=RangeConstraint(minimum=15.0, maximum=30.0),
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0),
        score_threshold=0.0,
        result_limit=5,
    )
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=criteria,
        satellite_group=SatelliteGroup.ACTIVE,
    )
    metric_calls: list[tuple[list[int], bool, bool]] = []
    session = _FakePassAnalysisSession(
        [accepted, metric_rejected],
        metric_values={
            1: (420.0, 20.0),
            2: (420.0, 35.0),
        },
        metric_calls=metric_calls,
    )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [accepted.satellite, metric_rejected.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: session,
    )

    response = engine.search_candidates(request)

    assert [candidate.satellite.tle.catalog_number for candidate in response.results] == [1]
    assert metric_calls[0] == ([1, 2], True, True)
    assert metric_rejected.metrics.satellite_altitude_km == 420.0
    assert metric_rejected.metrics.sun_proximity_deg == 35.0
    assert metric_rejected.diagnostics["rejection_reasons"] == ["sun_proximity"]


def test_returned_candidates_receive_public_metrics_even_when_filters_do_not_need_them(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchCriteria, SearchRequest

    candidate = _candidate(
        catalog_number=1,
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=SearchCriteria(score_threshold=0.0, result_limit=5),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    metric_calls: list[tuple[list[int], bool, bool]] = []
    session = _FakePassAnalysisSession(
        [candidate],
        metric_values={1: (421.5, 119.5)},
        metric_calls=metric_calls,
    )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: session,
    )

    response = engine.search_candidates(request)

    assert response.results[0].metrics.satellite_altitude_km == 421.5
    assert response.results[0].metrics.sun_proximity_deg == 119.5
    assert metric_calls == [
        ([1], False, False),
        ([1], True, True),
    ]


def test_search_candidates_reports_deterministic_stage_timing_diagnostics(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    candidate = _candidate()

    _patch_successful_pipeline(monkeypatch, engine, request, [candidate])

    response = engine.search_candidates(request, timer=DeterministicTimer())

    assert response.diagnostics["timings_ms"] == {
        "validation": 1.0,
        "interval_normalization": 1.0,
        "tle_loading": 1.0,
        "pass_analysis": 1.0,
        "geometry_filtering": 1.0,
        "metric_computation": 1.0,
        "metric_filtering": 1.0,
        "scoring": 1.0,
        "thresholding": 1.0,
        "ranking": 1.0,
        "limiting": 1.0,
        "response_metric_completion": 1.0,
        "total": 25.0,
    }


def test_search_candidates_keeps_serial_pass_analysis_as_default(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    candidate = _candidate(catalog_number=1)
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    received_geometry_kwargs: list[dict[str, Any]] = []

    class SerialRecordingSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(self, records, **kwargs):
            received_geometry_kwargs.append(kwargs)
            return _pass_analysis_result([candidate])

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: SerialRecordingSession([candidate]),
    )

    response = engine.search_candidates(request)

    assert received_geometry_kwargs == [{}]
    assert "parallel_search" not in response.diagnostics
    assert "parallel_search" not in response.diagnostics["pass_analysis"]


def test_search_candidates_passes_parallel_option_to_pass_analysis_boundary(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine, pass_analysis
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    candidate = _candidate(catalog_number=1)
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    expected_interval = (
        datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
    )
    config = pass_analysis.ParallelSearchConfig(
        enabled=True,
        requested_worker_count=4,
        chunk_size=16,
    )
    received_parallel_configs: list[pass_analysis.ParallelSearchConfig | None] = []

    class MetricCompletionSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(self, records, **kwargs):
            pytest.fail("parallel geometry must use the pass-analysis boundary")

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: MetricCompletionSession([candidate]),
    )

    def find_candidate_geometries_with_diagnostics(
        records,
        station,
        interval,
        *,
        candidate_budget=None,
        parallel_search=None,
    ):
        assert records == [candidate.satellite]
        assert station is request.station
        assert interval == expected_interval
        assert candidate_budget is None
        received_parallel_configs.append(parallel_search)
        return _pass_analysis_result(
            [candidate],
            {
                "satellite_records_inspected": 1,
                "candidate_geometries_found": 1,
                "skipped_record_count": 0,
                "skipped_records": [],
                "event_search_span": {
                    "start_utc": "2026-05-12T20:00:00Z",
                    "end_utc": "2026-05-12T20:10:00Z",
                },
                "parallel_search": {
                    "enabled": True,
                    "backend": "process_pool",
                    "requested_workers": 4,
                    "effective_workers": 4,
                    "chunk_size": 16,
                    "chunk_count": 1,
                },
            },
        )

    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_geometries_with_diagnostics",
        find_candidate_geometries_with_diagnostics,
    )

    response = engine.search_candidates(request, parallel_search=config)

    assert received_parallel_configs == [config]
    assert response.diagnostics["parallel_search"] == {
        "enabled": True,
        "backend": "process_pool",
        "requested_workers": 4,
        "effective_workers": 4,
        "chunk_size": 16,
        "chunk_count": 1,
    }
    json.dumps(response.diagnostics["parallel_search"])
    _assert_json_friendly(response.diagnostics["parallel_search"])


def test_approximate_budgeting_combines_with_parallel_when_requested(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine, pass_analysis
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    candidate = _candidate(catalog_number=1)
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    config = pass_analysis.ParallelSearchConfig(
        enabled=True,
        requested_worker_count=2,
        chunk_size=1,
    )
    received_kwargs: list[dict[str, Any]] = []

    class MetricCompletionSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(self, records, **kwargs):
            pytest.fail("parallel geometry must use the pass-analysis boundary")

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: MetricCompletionSession([candidate]),
    )

    def find_candidate_geometries_with_diagnostics(
        records,
        station,
        interval,
        *,
        candidate_budget=None,
        parallel_search=None,
    ):
        _ = records, station, interval
        received_kwargs.append(
            {
                "candidate_budget": candidate_budget,
                "parallel_search": parallel_search,
            }
        )
        assert parallel_search is config
        assert candidate_budget == 12
        return _pass_analysis_result(
            [candidate],
            {
                "satellite_records_inspected": 1,
                "candidate_geometries_found": 1,
                "skipped_record_count": 0,
                "skipped_records": [],
                "event_search_span": {
                    "start_utc": "2026-05-12T20:00:00Z",
                    "end_utc": "2026-05-12T20:10:00Z",
                },
                "candidate_budget": 12,
                "budget_reached": False,
                "processed_satellite_count": 1,
                "unprocessed_satellite_count": 0,
                "processed_candidate_count": 1,
                "parallel_search": {
                    "enabled": True,
                    "backend": "process_pool",
                    "requested_workers": 2,
                    "effective_workers": 2,
                    "chunk_size": 1,
                    "chunk_count": 1,
                },
            },
        )

    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_geometries_with_diagnostics",
        find_candidate_geometries_with_diagnostics,
    )

    response = engine.search_candidates(
        request,
        approximate_budgeted=True,
        parallel_search=config,
    )

    assert received_kwargs == [{"candidate_budget": 12, "parallel_search": config}]
    assert response.diagnostics["candidate_budget"] == {
        "requested": True,
        "enabled": True,
        "disabled_reason": None,
        "candidate_budget": 12,
        "budget_reached": False,
        "processed_satellite_count": 1,
        "unprocessed_satellite_count": 0,
        "processed_candidate_count": 1,
        "returned_candidate_count": 1,
        "approximate": False,
        "approximation_note": None,
    }
    assert response.diagnostics["search_optimization"]["approximate_budgeting"] is True
    assert response.diagnostics["parallel_search"]["enabled"] is True


def test_budgeted_parallel_results_are_marked_approximate_when_budget_is_reached(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine, pass_analysis
    from tlefinder.core.models import SatelliteGroup, SearchRequest

    candidate = _candidate(catalog_number=1)
    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(score_threshold=0.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    config = pass_analysis.ParallelSearchConfig(
        enabled=True,
        requested_worker_count=2,
        chunk_size=1,
    )
    received_kwargs: list[dict[str, Any]] = []

    class MetricCompletionSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(self, records, **kwargs):
            pytest.fail("parallel geometry must use the pass-analysis boundary")

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [
            _candidate(catalog_number=index).satellite for index in range(1, 7)
        ],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: MetricCompletionSession([candidate]),
    )

    def find_candidate_geometries_with_diagnostics(
        records,
        station,
        interval,
        *,
        candidate_budget=None,
        parallel_search=None,
    ):
        _ = station, interval
        received_kwargs.append(
            {
                "record_count": len(records),
                "candidate_budget": candidate_budget,
                "parallel_search": parallel_search,
            }
        )
        assert parallel_search is config
        assert candidate_budget == 12
        return _pass_analysis_result(
            [candidate],
            {
                "satellite_records_inspected": 4,
                "candidate_geometries_found": 12,
                "skipped_record_count": 0,
                "skipped_records": [],
                "event_search_span": {
                    "start_utc": "2026-05-12T20:00:00Z",
                    "end_utc": "2026-05-12T20:10:00Z",
                },
                "candidate_budget": 12,
                "budget_reached": True,
                "processed_satellite_count": 4,
                "unprocessed_satellite_count": 2,
                "processed_candidate_count": 12,
                "parallel_search": {
                    "enabled": True,
                    "backend": "process_pool",
                    "requested_workers": 2,
                    "effective_workers": 2,
                    "chunk_size": 1,
                    "chunk_count": 6,
                },
            },
        )

    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_geometries_with_diagnostics",
        find_candidate_geometries_with_diagnostics,
    )

    response = engine.search_candidates(
        request,
        approximate_budgeted=True,
        parallel_search=config,
    )

    assert received_kwargs == [
        {
            "record_count": 6,
            "candidate_budget": 12,
            "parallel_search": config,
        }
    ]
    assert response.diagnostics["candidate_budget"]["requested"] is True
    assert response.diagnostics["candidate_budget"]["enabled"] is True
    assert response.diagnostics["candidate_budget"]["disabled_reason"] is None
    assert response.diagnostics["candidate_budget"]["candidate_budget"] == 12
    assert response.diagnostics["candidate_budget"]["budget_reached"] is True
    assert response.diagnostics["candidate_budget"]["processed_satellite_count"] == 4
    assert response.diagnostics["candidate_budget"]["unprocessed_satellite_count"] == 2
    assert response.diagnostics["candidate_budget"]["processed_candidate_count"] == 12
    assert response.diagnostics["candidate_budget"]["returned_candidate_count"] == 1
    assert response.diagnostics["candidate_budget"]["approximate"] is True
    assert "unseen satellites" in response.diagnostics["candidate_budget"][
        "approximation_note"
    ]


def test_timing_diagnostics_do_not_change_candidate_ordering(
    monkeypatch,
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core import engine

    request = _request(station_factory, search_window_factory, search_criteria_factory)
    best = _candidate(catalog_number=2)
    second = _candidate(catalog_number=1)

    def run_search(timer=None):
        _patch_successful_pipeline(
            monkeypatch,
            engine,
            request,
            [second, best],
            ranked_candidates=[best, second],
        )
        return engine.search_candidates(request, timer=timer)

    untimed_response = run_search()
    timed_response = run_search(timer=DeterministicTimer())

    assert [
        candidate.satellite.tle.catalog_number for candidate in untimed_response.results
    ] == [2, 1]
    assert [
        candidate.satellite.tle.catalog_number for candidate in timed_response.results
    ] == [2, 1]


def test_budgeted_active_default_search_uses_six_times_result_limit_budget(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchCriteria, SearchRequest

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=SearchCriteria(score_threshold=0.0, result_limit=3),
        satellite_group=SatelliteGroup.ACTIVE,
    )
    candidate = _candidate(catalog_number=1)
    records = [candidate.satellite]
    received_budgets: list[int | None] = []

    class BudgetRecordingSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(
            self,
            records,
            *,
            candidate_budget=None,
        ):
            received_budgets.append(candidate_budget)
            return _pass_analysis_result(
                [candidate],
                {
                    "satellite_records_inspected": 1,
                    "candidate_geometries_found": 1,
                    "skipped_record_count": 0,
                    "skipped_records": [],
                    "event_search_span": {
                        "start_utc": "2026-05-12T20:00:00Z",
                        "end_utc": "2026-05-12T20:10:00Z",
                    },
                    "candidate_budget": 18,
                    "budget_reached": False,
                    "processed_satellite_count": 1,
                    "unprocessed_satellite_count": 0,
                    "processed_candidate_count": 1,
                },
            )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: BudgetRecordingSession([candidate]),
    )

    response = engine.search_candidates(request, approximate_budgeted=True)

    assert received_budgets == [18]
    assert response.diagnostics["candidate_budget"] == {
        "requested": True,
        "enabled": True,
        "disabled_reason": None,
        "candidate_budget": 18,
        "budget_reached": False,
        "processed_satellite_count": 1,
        "unprocessed_satellite_count": 0,
        "processed_candidate_count": 1,
        "returned_candidate_count": 1,
        "approximate": False,
        "approximation_note": None,
    }
    assert response.diagnostics["search_optimization"]["approximate_budgeting"] is True


def test_exact_search_mode_does_not_send_candidate_budget(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchCriteria, SearchRequest

    candidates = [_candidate(catalog_number=index) for index in range(1, 5)]
    records = [candidate.satellite for candidate in candidates]
    processed_record_counts: list[int] = []
    received_budgets: list[int | None] = []

    class ExactRecordingSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(
            self,
            records,
            *,
            candidate_budget=None,
        ):
            received_budgets.append(candidate_budget)
            processed_record_counts.append(len(records))
            return _pass_analysis_result(
                candidates,
                {
                    "satellite_records_inspected": len(records),
                    "candidate_geometries_found": len(candidates),
                    "skipped_record_count": 0,
                    "skipped_records": [],
                    "event_search_span": {
                        "start_utc": "2026-05-12T20:00:00Z",
                        "end_utc": "2026-05-12T20:10:00Z",
                    },
                },
            )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: ExactRecordingSession(candidates),
    )

    response = engine.search_candidates(
        SearchRequest(
            station=station_factory(),
            window=search_window_factory(),
            criteria=SearchCriteria(score_threshold=0.0, result_limit=1),
            satellite_group=SatelliteGroup.ACTIVE,
        ),
        approximate_budgeted=False,
    )

    assert received_budgets == [None]
    assert processed_record_counts == [4]
    assert response.diagnostics["candidate_budget"]["enabled"] is False
    assert response.diagnostics["candidate_budget"]["processed_satellite_count"] == 4
    assert response.diagnostics["candidate_budget"]["unprocessed_satellite_count"] == 0


def test_budgeted_search_is_disabled_for_strict_hard_filters(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
    )

    candidate = _candidate(catalog_number=1)
    received_budgets: list[int | None] = []

    class StrictFilterSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(
            self,
            records,
            *,
            candidate_budget=None,
        ):
            received_budgets.append(candidate_budget)
            return _pass_analysis_result([candidate])

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: StrictFilterSession([candidate]),
    )

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=SearchCriteria(
            culmination_altitude_deg=RangeConstraint(minimum=30.0),
            score_threshold=0.0,
            result_limit=1,
        ),
        satellite_group=SatelliteGroup.ACTIVE,
    )

    response = engine.search_candidates(request, approximate_budgeted=True)

    assert received_budgets == [None]
    assert response.diagnostics["candidate_budget"]["requested"] is True
    assert response.diagnostics["candidate_budget"]["enabled"] is False
    assert response.diagnostics["candidate_budget"]["disabled_reason"] == "strict_filters"
    assert response.diagnostics["search_optimization"]["approximate_budgeting"] is False


def test_strict_filters_disable_approximate_budgeting_even_with_parallel_enabled(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine, pass_analysis
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
    )

    candidate = _candidate(catalog_number=1)
    config = pass_analysis.ParallelSearchConfig(
        enabled=True,
        requested_worker_count=2,
        chunk_size=1,
    )
    received_kwargs: list[dict[str, Any]] = []

    class MetricCompletionSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(self, records, **kwargs):
            pytest.fail("parallel geometry must use the pass-analysis boundary")

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: MetricCompletionSession([candidate]),
    )

    def find_candidate_geometries_with_diagnostics(
        records,
        station,
        interval,
        *,
        candidate_budget=None,
        parallel_search=None,
    ):
        _ = records, station, interval
        received_kwargs.append(
            {
                "candidate_budget": candidate_budget,
                "parallel_search": parallel_search,
            }
        )
        assert parallel_search is config
        return _pass_analysis_result(
            [candidate],
            {
                "satellite_records_inspected": 1,
                "candidate_geometries_found": 1,
                "skipped_record_count": 0,
                "skipped_records": [],
                "event_search_span": {
                    "start_utc": "2026-05-12T20:00:00Z",
                    "end_utc": "2026-05-12T20:10:00Z",
                },
                "parallel_search": {
                    "enabled": True,
                    "backend": "process_pool",
                    "requested_workers": 2,
                    "effective_workers": 2,
                    "chunk_size": 1,
                    "chunk_count": 1,
                },
            },
        )

    monkeypatch.setattr(
        engine.pass_analysis,
        "find_candidate_geometries_with_diagnostics",
        find_candidate_geometries_with_diagnostics,
    )

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=SearchCriteria(
            culmination_altitude_deg=RangeConstraint(minimum=30.0),
            score_threshold=0.0,
            result_limit=1,
        ),
        satellite_group=SatelliteGroup.ACTIVE,
    )

    response = engine.search_candidates(
        request,
        approximate_budgeted=True,
        parallel_search=config,
    )

    assert received_kwargs == [{"candidate_budget": None, "parallel_search": config}]
    assert response.diagnostics["candidate_budget"]["requested"] is True
    assert response.diagnostics["candidate_budget"]["enabled"] is False
    assert response.diagnostics["candidate_budget"]["disabled_reason"] == "strict_filters"
    assert response.diagnostics["search_optimization"]["approximate_budgeting"] is False
    assert response.diagnostics["parallel_search"]["enabled"] is True


def test_budgeted_search_allows_simple_default_broad_filters(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import (
        RangeConstraint,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
    )

    candidate = _candidate(catalog_number=1)
    received_budgets: list[int | None] = []

    class SimpleDefaultSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(
            self,
            records,
            *,
            candidate_budget=None,
        ):
            received_budgets.append(candidate_budget)
            return _pass_analysis_result(
                [candidate],
                {
                    "satellite_records_inspected": 1,
                    "candidate_geometries_found": 1,
                    "skipped_record_count": 0,
                    "skipped_records": [],
                    "event_search_span": {
                        "start_utc": "2026-05-12T20:00:00Z",
                        "end_utc": "2026-05-12T20:10:00Z",
                    },
                    "candidate_budget": 60,
                    "budget_reached": False,
                    "processed_satellite_count": 1,
                    "unprocessed_satellite_count": 0,
                    "processed_candidate_count": 1,
                },
            )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: [candidate.satellite],
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: SimpleDefaultSession([candidate]),
    )

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=SearchCriteria(
            culmination_altitude_deg=RangeConstraint(minimum=0.0, maximum=90.0),
            sun_proximity_deg=RangeConstraint(minimum=0.0, maximum=180.0),
            satellite_altitude_km=RangeConstraint(minimum=200.0, maximum=2000.0),
            score_threshold=0.0,
            result_limit=10,
        ),
        satellite_group=SatelliteGroup.ACTIVE,
    )

    response = engine.search_candidates(request, approximate_budgeted=True)

    assert received_budgets == [60]
    assert response.diagnostics["candidate_budget"]["enabled"] is True
    assert response.diagnostics["candidate_budget"]["candidate_budget"] == 60
    assert response.diagnostics["search_optimization"]["approximate_budgeting"] is True


def test_budgeted_results_are_ranked_and_limited_from_processed_shortlist(
    monkeypatch,
    station_factory,
    search_window_factory,
):
    from tlefinder.core import engine
    from tlefinder.core.models import SatelliteGroup, SearchCriteria, SearchRequest

    candidates = [_candidate(catalog_number=index) for index in range(1, 9)]
    records = [candidate.satellite for candidate in candidates]
    processed_candidates = candidates[:6]
    scores = {
        1: 55.0,
        2: 70.0,
        3: 80.0,
        4: 65.0,
        5: 95.0,
        6: 75.0,
    }

    class BudgetedShortlistSession(_FakePassAnalysisSession):
        def find_candidate_geometries_with_diagnostics(
            self,
            records,
            *,
            candidate_budget=None,
        ):
            assert candidate_budget == 6
            return _pass_analysis_result(
                processed_candidates,
                {
                    "satellite_records_inspected": 6,
                    "candidate_geometries_found": 6,
                    "skipped_record_count": 0,
                    "skipped_records": [],
                    "event_search_span": {
                        "start_utc": "2026-05-12T20:00:00Z",
                        "end_utc": "2026-05-12T20:10:00Z",
                    },
                    "candidate_budget": 6,
                    "budget_reached": True,
                    "processed_satellite_count": 6,
                    "unprocessed_satellite_count": 2,
                    "processed_candidate_count": 6,
                },
            )

    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: BudgetedShortlistSession(processed_candidates),
    )
    monkeypatch.setattr(
        engine.scoring,
        "compute_match_score",
        lambda candidate, criteria, interval: _set_score(
            candidate,
            scores[candidate.satellite.tle.catalog_number],
        ),
    )

    response = engine.search_candidates(
        SearchRequest(
            station=station_factory(),
            window=search_window_factory(),
            criteria=SearchCriteria(score_threshold=0.0, result_limit=1),
            satellite_group=SatelliteGroup.ACTIVE,
        ),
        approximate_budgeted=True,
    )

    assert [candidate.satellite.tle.catalog_number for candidate in response.results] == [5]
    assert response.results[0].rank == 1
    assert response.results[0].match_score == 95.0
    assert response.diagnostics["candidate_budget"]["budget_reached"] is True
    assert response.diagnostics["candidate_budget"]["processed_candidate_count"] == 6
    assert response.diagnostics["candidate_budget"]["returned_candidate_count"] == 1
    assert response.diagnostics["candidate_budget"]["approximate"] is True
    assert "unseen satellites" in response.diagnostics["candidate_budget"][
        "approximation_note"
    ]


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


def _set_score(candidate, score: float):
    candidate.match_score = score
    return candidate


def _set_rank(candidate, rank: int):
    candidate.rank = rank
    return candidate


def _result_signature(candidates):
    return [
        (
            candidate.satellite.tle.catalog_number,
            round(candidate.match_score, 6),
            candidate.rank,
            candidate.diagnostics,
            candidate.metrics.satellite_altitude_km,
            candidate.metrics.sun_proximity_deg,
        )
        for candidate in candidates
    ]


def _patch_successful_pipeline(
    monkeypatch,
    engine,
    request,
    candidates,
    *,
    ranked_candidates=None,
    pass_diagnostics: dict[str, Any] | None = None,
) -> None:
    interval = (
        datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
    )
    records = [candidate.satellite for candidate in candidates]

    monkeypatch.setattr(engine.validation, "validate_search_request", lambda request: None)
    monkeypatch.setattr(
        engine.time_utils,
        "build_search_interval",
        lambda window: interval,
    )
    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession(
            candidates,
            diagnostics=pass_diagnostics,
        ),
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_geometry_candidate_passes",
        lambda candidates, criteria: candidates,
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_metric_candidate_passes",
        lambda candidates, criteria: candidates,
    )
    monkeypatch.setattr(
        engine.scoring,
        "compute_match_score",
        lambda candidate, criteria, interval: _set_score(candidate, 80.0),
    )
    monkeypatch.setattr(
        engine.ranking,
        "apply_score_threshold",
        lambda candidates, threshold: candidates,
    )

    def rank_candidates(candidates):
        selected = list(candidates if ranked_candidates is None else ranked_candidates)
        return [_set_rank(candidate, index) for index, candidate in enumerate(selected, start=1)]

    monkeypatch.setattr(engine.ranking, "rank_candidates", rank_candidates)
    monkeypatch.setattr(
        engine.ranking,
        "limit_results",
        lambda candidates, limit: candidates[:limit],
    )


class _FakePassAnalysisSession:
    def __init__(
        self,
        candidates,
        *,
        diagnostics: dict[str, Any] | None = None,
        metric_values: dict[int, tuple[float, float | None]] | None = None,
        metric_calls: list[tuple[list[int], bool, bool]] | None = None,
    ):
        self._candidates = list(candidates)
        self._diagnostics = diagnostics
        self._metric_values = metric_values or {}
        self.metric_calls = [] if metric_calls is None else metric_calls

    def find_candidate_geometries_with_diagnostics(self, records):
        return _pass_analysis_result(self._candidates, self._diagnostics)

    def compute_required_metrics(
        self,
        candidates,
        *,
        include_satellite_altitude,
        include_sun_proximity,
    ):
        from tlefinder.core.models import PassMetrics

        candidate_list = list(candidates)
        self.metric_calls.append(
            (
                [
                    candidate.satellite.tle.catalog_number
                    for candidate in candidate_list
                ],
                include_satellite_altitude,
                include_sun_proximity,
            )
        )
        for candidate in candidate_list:
            altitude, sun = self._metric_values.get(
                candidate.satellite.tle.catalog_number,
                (420.0, 25.0),
            )
            candidate.metrics = PassMetrics(
                satellite_altitude_km=(
                    altitude
                    if include_satellite_altitude
                    else candidate.metrics.satellite_altitude_km
                ),
                sun_proximity_deg=(
                    sun
                    if include_sun_proximity
                    else candidate.metrics.sun_proximity_deg
                ),
            )
        return candidate_list


def _assert_json_friendly(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_friendly(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_friendly(item)
        return
    raise AssertionError(f"non-JSON diagnostic value: {value!r}")
