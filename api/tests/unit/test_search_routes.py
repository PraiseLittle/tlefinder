from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


pytestmark = pytest.mark.unit


def search_station_payload(**overrides):
    payload = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    payload.update(overrides)
    return payload


def unnamed_station_payload():
    return {
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }


def search_window_payload(**overrides):
    payload = {
        "start_at": "2026-05-12T20:00:00Z",
        "duration_minutes": 10,
    }
    payload.update(overrides)
    return payload


def simple_search_payload(**overrides):
    payload = {
        "station": search_station_payload(),
        "window": search_window_payload(),
    }
    payload.update(overrides)
    return payload


def advanced_search_payload(**overrides):
    payload = {
        "station": unnamed_station_payload(),
        "window": search_window_payload(),
        "satellite_group": "visual",
        "criteria": {
            "culmination_altitude_deg": {"minimum": 20, "maximum": 80},
            "start_azimuth_deg": {"target": 270, "tolerance": 20},
            "sun_proximity_deg": {"minimum": 30, "maximum": 180},
            "satellite_altitude_km": {"minimum": 400, "maximum": 1200},
            "result_limit": 5,
            "score_threshold": 60,
        },
    }
    payload.update(overrides)
    return payload


def api_client(tmp_path, *, raise_server_exceptions=True, settings=None):
    from tlefinder.api.app import create_app
    from tlefinder.api.config import ApiSettings

    store_path = tmp_path / "stations.yaml"
    resolved_settings = settings or ApiSettings(
        station_store_path=store_path,
        tle_cache_dir=tmp_path / "tle-cache",
    )
    client = TestClient(
        create_app(resolved_settings),
        raise_server_exceptions=raise_server_exceptions,
    )
    return client, store_path


def core_no_result_response():
    from tlefinder.core.models import SearchResponse, SearchStatus

    return SearchResponse(
        results=[],
        status=SearchStatus.NO_RESULT,
        diagnostics={
            "satellite_count": 1200,
            "candidate_count": 0,
            "returned_count": 0,
        },
    )


def core_result_response():
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        SearchResponse,
        SearchStatus,
        TleRecord,
    )

    candidate = CandidatePass(
        satellite=SatelliteRecord(
            tle=TleRecord(
                name="ISS (ZARYA)",
                line1="1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                line2="2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                catalog_number=25544,
                epoch_utc=datetime(2026, 5, 12, 14, 12, tzinfo=timezone.utc),
                source_group=SatelliteGroup.ACTIVE,
                source_path=Path("active.tle"),
            )
        ),
        geometry=PassGeometry(
            start_time_utc=datetime(2026, 5, 12, 20, 2, 10, tzinfo=timezone.utc),
            end_time_utc=datetime(2026, 5, 12, 20, 8, 42, tzinfo=timezone.utc),
            culmination_time_utc=datetime(2026, 5, 12, 20, 5, 20, tzinfo=timezone.utc),
            start_azimuth_deg=252.1,
            end_azimuth_deg=63.4,
            culmination_azimuth_deg=319.8,
            culmination_altitude_deg=71.2,
        ),
        metrics=PassMetrics(satellite_altitude_km=420.5, sun_proximity_deg=118.0),
        match_score=87.5,
        rank=1,
    )
    return SearchResponse(
        results=[candidate],
        status=SearchStatus.RESULTS,
        diagnostics={"returned_count": 1},
    )


def test_simple_search_adapts_request_and_calls_core_once(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.models import SatelliteGroup, TleAgeLimit

    client, _store_path = api_client(tmp_path)
    received_requests = []
    received_kwargs = []
    events = []

    def search_candidates(core_request, **kwargs):
        events.append("search")
        received_requests.append(core_request)
        received_kwargs.append(kwargs)
        return core_result_response()

    def add_station_if_new(path, station):
        events.append("persist")
        return []

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        add_station_if_new,
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 200
    assert len(received_requests) == 1
    core_request = received_requests[0]
    assert core_request.satellite_group is SatelliteGroup.ACTIVE
    assert core_request.tle_age_limit is TleAgeLimit.HOURS_24
    assert core_request.criteria.result_limit == 10
    assert core_request.criteria.score_threshold == 0.0
    assert received_kwargs == [
        {
            "cache_dir": tmp_path / "tle-cache",
            "approximate_budgeted": True,
        }
    ]
    assert response.json()["results"][0]["rank"] == 1
    assert events == ["search", "persist"]


def test_advanced_search_adapts_request_and_calls_core_once(monkeypatch, tmp_path):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.models import SatelliteGroup, TleAgeLimit

    client, _store_path = api_client(tmp_path)
    received_requests = []
    received_kwargs = []

    def search_candidates(core_request, **kwargs):
        received_requests.append(core_request)
        received_kwargs.append(kwargs)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: pytest.fail("unnamed stations must not be persisted"),
    )

    response = client.post(
        "/api/v1/search/advanced",
        json=advanced_search_payload(tle_age_limit="1w"),
    )

    assert response.status_code == 200
    assert len(received_requests) == 1
    core_request = received_requests[0]
    assert core_request.satellite_group is SatelliteGroup.VISUAL
    assert core_request.tle_age_limit is TleAgeLimit.WEEK_1
    assert core_request.criteria.culmination_altitude_deg.minimum == 20.0
    assert core_request.criteria.start_azimuth_deg.target == 270.0
    assert core_request.criteria.result_limit == 5
    assert core_request.criteria.score_threshold == 60.0
    assert received_kwargs == [{"cache_dir": tmp_path / "tle-cache"}]


def test_simple_search_uses_server_configured_parallel_budgeted_mode(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.config import ApiSettings
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core import pass_analysis

    settings = ApiSettings(
        station_store_path=tmp_path / "stations.yaml",
        tle_cache_dir=tmp_path / "tle-cache",
        parallel_search_enabled=True,
        parallel_worker_count=4,
        parallel_chunk_size=16,
    )
    client, _store_path = api_client(tmp_path, settings=settings)
    received_kwargs = []

    def search_candidates(core_request, **kwargs):
        received_kwargs.append(kwargs)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: [],
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 200
    assert len(received_kwargs) == 1
    assert received_kwargs[0]["approximate_budgeted"] is True
    assert received_kwargs[0]["cache_dir"] == tmp_path / "tle-cache"
    config = received_kwargs[0]["parallel_search"]
    assert isinstance(config, pass_analysis.ParallelSearchConfig)
    assert config.enabled is True
    assert config.requested_worker_count == 4
    assert config.effective_worker_count == 4
    assert config.chunk_size == 16


def test_advanced_search_uses_server_configured_exact_parallel_mode(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.config import ApiSettings
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core import pass_analysis

    settings = ApiSettings(
        station_store_path=tmp_path / "stations.yaml",
        tle_cache_dir=tmp_path / "tle-cache",
        parallel_search_enabled=True,
        parallel_worker_count=3,
        parallel_chunk_size=8,
    )
    client, _store_path = api_client(tmp_path, settings=settings)
    received_kwargs = []

    def search_candidates(core_request, **kwargs):
        received_kwargs.append(kwargs)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post("/api/v1/search/advanced", json=advanced_search_payload())

    assert response.status_code == 200
    assert len(received_kwargs) == 1
    assert "approximate_budgeted" not in received_kwargs[0]
    assert received_kwargs[0]["cache_dir"] == tmp_path / "tle-cache"
    config = received_kwargs[0]["parallel_search"]
    assert isinstance(config, pass_analysis.ParallelSearchConfig)
    assert config.enabled is True
    assert config.requested_worker_count == 3
    assert config.effective_worker_count == 3
    assert config.chunk_size == 8


def test_search_routes_delegate_domain_workflow_to_core_entrypoint(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes
    import tlefinder.core.filtering as filtering
    import tlefinder.core.pass_analysis as pass_analysis
    import tlefinder.core.ranking as ranking
    import tlefinder.core.scoring as scoring
    import tlefinder.core.tle_repository as tle_repository

    client, _store_path = api_client(tmp_path)

    def forbidden_call(*args, **kwargs):
        raise AssertionError("route must delegate search workflow to core.search_candidates")

    monkeypatch.setattr(pass_analysis, "find_candidate_passes", forbidden_call)
    monkeypatch.setattr(filtering, "filter_candidate_passes", forbidden_call)
    monkeypatch.setattr(scoring, "compute_match_score", forbidden_call)
    monkeypatch.setattr(ranking, "rank_candidates", forbidden_call)
    monkeypatch.setattr(tle_repository, "load_tle_dataset", forbidden_call)
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda request, **kwargs: core_no_result_response(),
    )
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: [],
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 200


def test_no_result_core_response_returns_http_200_success_payload(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client(tmp_path)
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda request, **kwargs: core_no_result_response(),
    )
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: [],
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 200
    assert response.json()["status"] == "no_result"
    assert response.json()["results"] == []


def test_named_stations_are_not_persisted_when_search_execution_fails(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.errors import TleLoadError

    client, _store_path = api_client(tmp_path)

    def fail_search(core_request, **kwargs):
        raise TleLoadError("TLE data unavailable")

    monkeypatch.setattr(search_routes.core, "search_candidates", fail_search)
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: pytest.fail("station must not persist after search failure"),
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "tle_unavailable"


def test_unnamed_search_station_is_not_persisted_after_success(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client(tmp_path)
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda request, **kwargs: core_no_result_response(),
    )
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: pytest.fail("unnamed stations must not be persisted"),
    )

    response = client.post(
        "/api/v1/search/simple",
        json=simple_search_payload(station=unnamed_station_payload()),
    )

    assert response.status_code == 200


def test_persistence_failure_after_successful_search_returns_explicit_error(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client(tmp_path)
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda request, **kwargs: core_no_result_response(),
    )

    def fail_persistence(path, station):
        raise StationStoreError("Station store could not be saved.")

    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        fail_persistence,
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "station_store_error"
    assert response.json()["error"]["message"] == "Station store could not be saved."
