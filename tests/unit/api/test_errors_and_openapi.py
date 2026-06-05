from __future__ import annotations

from fastapi.testclient import TestClient
import pytest


pytestmark = pytest.mark.unit


def station_payload(**overrides):
    payload = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    payload.update(overrides)
    return payload


def simple_search_payload(**overrides):
    payload = {
        "station": station_payload(),
        "window": {
            "start_at": "2026-05-12T20:00:00Z",
            "duration_minutes": 10,
        },
    }
    payload.update(overrides)
    return payload


def api_client(tmp_path, *, raise_server_exceptions=True):
    from tlefinder.api.app import create_app
    from tlefinder.api.config import ApiSettings

    return TestClient(
        create_app(ApiSettings(station_store_path=tmp_path / "stations.yaml")),
        raise_server_exceptions=raise_server_exceptions,
    )


def core_no_result_response():
    from tlefinder.core.models import SearchResponse, SearchStatus

    return SearchResponse(results=[], status=SearchStatus.NO_RESULT, diagnostics={})


def test_pydantic_request_validation_errors_map_to_422_envelope(tmp_path):
    client = api_client(tmp_path)

    response = client.post(
        "/api/v1/search/simple",
        json=simple_search_payload(
            window={"start_at": "2026-05-12T20:00:00Z", "duration_minutes": 0}
        ),
    )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["field_errors"][0]["field"] == "window.duration_minutes"


@pytest.mark.parametrize(
    ("exception_factory", "status_code", "error_code"),
    [
        pytest.param(
            lambda: __import__(
                "tlefinder.core.errors",
                fromlist=["ValidationError"],
            ).ValidationError("Core request validation failed."),
            422,
            "validation_error",
            id="core-validation",
        ),
        pytest.param(
            lambda: __import__(
                "tlefinder.core.errors",
                fromlist=["TleLoadError"],
            ).TleLoadError("TLE data unavailable"),
            503,
            "tle_unavailable",
            id="tle-load",
        ),
        pytest.param(
            lambda: __import__(
                "tlefinder.core.errors",
                fromlist=["TleFreshnessError"],
            ).TleFreshnessError("TLE data is stale"),
            503,
            "tle_stale",
            id="tle-stale",
        ),
        pytest.param(
            lambda: __import__(
                "tlefinder.core.errors",
                fromlist=["SearchExecutionError"],
            ).SearchExecutionError("Search execution failed"),
            500,
            "search_execution_error",
            id="search-execution",
        ),
    ],
)
def test_core_exceptions_map_to_stable_error_codes(
    monkeypatch,
    tmp_path,
    exception_factory,
    status_code,
    error_code,
):
    from tlefinder.api.routers import search as search_routes

    client = api_client(tmp_path)

    def fail_search(core_request, **kwargs):
        raise exception_factory()

    monkeypatch.setattr(search_routes.core, "search_candidates", fail_search)
    monkeypatch.setattr(
        search_routes.station_store,
        "add_station_if_new",
        lambda *args: pytest.fail("persistence must not run after core failure"),
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    assert "traceback" not in response.text.lower()


def test_station_validation_error_maps_to_422_envelope(monkeypatch, tmp_path):
    from tlefinder.api.errors import ApiFieldError, StationValidationError
    from tlefinder.api.routers import stations as station_routes

    client = api_client(tmp_path)

    def fail_replace(path, stations):
        raise StationValidationError(
            field_errors=[
                ApiFieldError(field="stations.0.name", message="name must not be empty")
            ]
        )

    monkeypatch.setattr(
        station_routes.station_store,
        "replace_stations",
        fail_replace,
    )

    response = client.put(
        "/api/v1/stations",
        json={"stations": [station_payload()]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "station_validation_error"
    assert response.json()["error"]["field_errors"] == [
        {"field": "stations.0.name", "message": "name must not be empty"}
    ]


def test_station_store_error_maps_to_500_envelope(monkeypatch, tmp_path):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.routers import stations as station_routes

    client = api_client(tmp_path)

    def fail_load(path):
        raise StationStoreError("Station store could not be loaded.")

    monkeypatch.setattr(station_routes.station_store, "load_stations", fail_load)

    response = client.get("/api/v1/stations")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "station_store_error"
    assert response.json()["error"]["message"] == "Station store could not be loaded."


def test_unexpected_exceptions_map_to_generic_internal_error_without_traceback(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import search as search_routes

    client = api_client(tmp_path, raise_server_exceptions=False)

    def fail_search(core_request, **kwargs):
        raise RuntimeError("secret backend implementation detail")

    monkeypatch.setattr(search_routes.core, "search_candidates", fail_search)

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret backend implementation detail" not in response.text
    assert "traceback" not in response.text.lower()


def test_openapi_registers_public_api_routes(tmp_path):
    client = api_client(tmp_path)

    openapi = client.get("/openapi.json").json()

    assert "/api/v1/stations" in openapi["paths"]
    assert "get" in openapi["paths"]["/api/v1/stations"]
    assert "put" in openapi["paths"]["/api/v1/stations"]
    assert "/api/v1/search/simple" in openapi["paths"]
    assert "post" in openapi["paths"]["/api/v1/search/simple"]
    assert "/api/v1/search/advanced" in openapi["paths"]
    assert "post" in openapi["paths"]["/api/v1/search/advanced"]


def test_openapi_exposes_stable_public_schemas_and_error_responses(tmp_path):
    client = api_client(tmp_path)

    openapi = client.get("/openapi.json").json()
    schemas = openapi["components"]["schemas"]

    for schema_name in (
        "SimpleSearchRequest",
        "AdvancedSearchRequest",
        "StationListRequest",
        "StationListResponse",
        "SearchResponse",
        "ErrorResponse",
    ):
        assert schema_name in schemas

    simple_search_responses = openapi["paths"]["/api/v1/search/simple"]["post"][
        "responses"
    ]
    station_put_responses = openapi["paths"]["/api/v1/stations"]["put"]["responses"]

    assert "422" in simple_search_responses
    assert "500" in simple_search_responses
    assert "503" in simple_search_responses
    assert "422" in station_put_responses
    assert "500" in station_put_responses
