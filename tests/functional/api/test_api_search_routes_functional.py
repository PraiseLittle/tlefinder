from __future__ import annotations

import pytest


pytestmark = pytest.mark.functional


def test_simple_search_returns_ranked_result_from_controlled_core_response(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    core_result_response,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda core_request: core_result_response(),
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "results"
    assert body["results"][0]["rank"] == 1
    assert body["results"][0]["match_score"] == 87.5
    assert body["results"][0]["satellite"]["name"] == "ISS (ZARYA)"
    assert body["results"][0]["geometry"]["start_time_utc"] == "2026-05-12T20:02:10Z"
    assert body["diagnostics"]["returned_count"] == 1


def test_simple_search_defaults_are_visible_in_core_request(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.models import SatelliteGroup

    client, _store_path = api_client_factory()
    captured_requests = []

    def search_candidates(core_request):
        captured_requests.append(core_request)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 200
    assert len(captured_requests) == 1
    core_request = captured_requests[0]
    assert core_request.satellite_group is SatelliteGroup.ACTIVE
    assert core_request.criteria.culmination_altitude_deg.minimum == 0.0
    assert core_request.criteria.culmination_altitude_deg.maximum == 90.0
    assert core_request.criteria.start_azimuth_deg is None
    assert core_request.criteria.end_azimuth_deg is None
    assert core_request.criteria.culmination_azimuth_deg is None
    assert core_request.criteria.sun_proximity_deg.minimum == 0.0
    assert core_request.criteria.sun_proximity_deg.maximum == 180.0
    assert core_request.criteria.satellite_altitude_km.minimum == 200.0
    assert core_request.criteria.satellite_altitude_km.maximum == 2000.0
    assert core_request.criteria.result_limit == 10
    assert core_request.criteria.score_threshold == 0.0


def test_simple_search_no_result_returns_success_with_empty_results(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    unnamed_station_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda core_request: core_no_result_response(),
    )

    response = client.post(
        "/api/v1/search/simple",
        json=simple_search_payload(station=unnamed_station_payload()),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "no_result"
    assert response.json()["results"] == []


def test_named_station_from_successful_simple_search_is_persisted(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    station_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()
    station = station_payload()
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda core_request: core_no_result_response(),
    )

    search_response = client.post(
        "/api/v1/search/simple",
        json=simple_search_payload(station=station),
    )

    assert search_response.status_code == 200
    assert client.get("/api/v1/stations").json() == {"stations": [station]}


def test_invalid_simple_search_request_does_not_call_core(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    search_window_payload,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()

    def search_candidates(core_request):
        pytest.fail("core search must not run after request validation failure")

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post(
        "/api/v1/search/simple",
        json=simple_search_payload(
            window=search_window_payload(duration_minutes=0),
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_advanced_search_maps_supported_criteria_into_core_request(
    api_client_factory,
    monkeypatch,
    advanced_search_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.models import SatelliteGroup

    client, _store_path = api_client_factory()
    captured_requests = []

    def search_candidates(core_request):
        captured_requests.append(core_request)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post("/api/v1/search/advanced", json=advanced_search_payload())

    assert response.status_code == 200
    assert len(captured_requests) == 1
    criteria = captured_requests[0].criteria
    assert captured_requests[0].satellite_group is SatelliteGroup.VISUAL
    assert criteria.culmination_altitude_deg.minimum == 20.0
    assert criteria.culmination_altitude_deg.maximum == 80.0
    assert criteria.culmination_altitude_target_deg.target == 55.0
    assert criteria.culmination_altitude_target_deg.tolerance == 12.0
    assert criteria.start_azimuth_deg.target == 270.0
    assert criteria.end_azimuth_deg.target == 90.0
    assert criteria.culmination_azimuth_deg.target == 180.0
    assert criteria.sun_proximity_deg.minimum == 30.0
    assert criteria.satellite_altitude_km.maximum == 1200.0


def test_unsupported_advanced_criteria_return_machine_readable_422(
    api_client_factory,
    monkeypatch,
    advanced_search_payload,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()

    def search_candidates(core_request):
        pytest.fail("core search must not run for unsupported API criteria")

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post(
        "/api/v1/search/advanced",
        json=advanced_search_payload(
            criteria={
                "object_type": "payload",
                "result_limit": 5,
            }
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["field_errors"][0]["field"] == "criteria.object_type"


def test_advanced_search_passes_threshold_and_result_limit_to_core(
    api_client_factory,
    monkeypatch,
    advanced_search_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()
    captured_requests = []

    def search_candidates(core_request):
        captured_requests.append(core_request)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post(
        "/api/v1/search/advanced",
        json=advanced_search_payload(
            criteria={
                "result_limit": 3,
                "score_threshold": 75,
            }
        ),
    )

    assert response.status_code == 200
    assert captured_requests[0].criteria.result_limit == 3
    assert captured_requests[0].criteria.score_threshold == 75.0


@pytest.mark.parametrize("satellite_group", ["active", "visual", "amateur"])
def test_supported_satellite_groups_are_accepted(
    api_client_factory,
    monkeypatch,
    advanced_search_payload,
    core_no_result_response,
    satellite_group,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core.models import SatelliteGroup

    client, _store_path = api_client_factory()
    captured_requests = []

    def search_candidates(core_request):
        captured_requests.append(core_request)
        return core_no_result_response()

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post(
        "/api/v1/search/advanced",
        json=advanced_search_payload(satellite_group=satellite_group),
    )

    assert response.status_code == 200
    assert captured_requests[0].satellite_group is SatelliteGroup(satellite_group)


def test_invalid_satellite_group_returns_machine_readable_validation_error(
    api_client_factory,
    monkeypatch,
    advanced_search_payload,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory()

    def search_candidates(core_request):
        pytest.fail("core search must not run for invalid satellite groups")

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post(
        "/api/v1/search/advanced",
        json=advanced_search_payload(satellite_group="weather"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["field_errors"][0]["field"] == "satellite_group"
