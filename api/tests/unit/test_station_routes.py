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


def station_route_client(tmp_path):
    from tlefinder.api.app import create_app
    from tlefinder.api.config import ApiSettings

    store_path = tmp_path / "stations.yaml"
    client = TestClient(create_app(ApiSettings(station_store_path=store_path)))
    return client, store_path


def test_get_stations_calls_station_store_and_returns_persisted_list(
    monkeypatch,
    tmp_path,
):
    from tlefinder.api.routers import stations as station_routes
    from tlefinder.api.schemas import PersistedStation

    client, store_path = station_route_client(tmp_path)
    received_paths = []

    def load_stations(path):
        received_paths.append(path)
        return [PersistedStation.model_validate(station_payload())]

    monkeypatch.setattr(station_routes.station_store, "load_stations", load_stations)

    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    assert received_paths == [store_path]
    assert response.json() == {"stations": [station_payload()]}


def test_get_stations_creates_empty_station_list_on_first_access(tmp_path):
    import yaml

    client, store_path = station_route_client(tmp_path)

    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    assert response.json() == {"stations": []}
    assert yaml.safe_load(store_path.read_text(encoding="utf-8")) == {"stations": []}


def test_put_stations_replaces_complete_station_list(monkeypatch, tmp_path):
    from tlefinder.api.routers import stations as station_routes
    from tlefinder.api.schemas import PersistedStation

    client, store_path = station_route_client(tmp_path)
    submitted = [
        station_payload(),
        station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503),
    ]
    received = []

    def replace_stations(path, stations):
        received.append((path, [station.model_dump(mode="json") for station in stations]))
        return [PersistedStation.model_validate(station) for station in submitted]

    monkeypatch.setattr(
        station_routes.station_store,
        "replace_stations",
        replace_stations,
    )

    response = client.put("/api/v1/stations", json={"stations": submitted})

    assert response.status_code == 200
    assert received == [(store_path, submitted)]
    assert response.json() == {"stations": submitted}


def test_put_invalid_station_replacement_returns_machine_readable_422(tmp_path):
    client, store_path = station_route_client(tmp_path)
    valid_station = station_payload()

    first_response = client.put("/api/v1/stations", json={"stations": [valid_station]})
    assert first_response.status_code == 200
    previous_text = store_path.read_text(encoding="utf-8")

    response = client.put(
        "/api/v1/stations",
        json={
            "stations": [
                station_payload(name="Paris A"),
                station_payload(name="Paris B"),
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "station_validation_error"
    assert response.json()["error"]["field_errors"][0]["field"] == "stations.1"
    assert store_path.read_text(encoding="utf-8") == previous_text


def test_station_store_failures_return_machine_readable_500(monkeypatch, tmp_path):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.routers import stations as station_routes

    client, _store_path = station_route_client(tmp_path)

    def fail_load(path):
        raise StationStoreError("Station store could not be loaded.")

    monkeypatch.setattr(station_routes.station_store, "load_stations", fail_load)

    response = client.get("/api/v1/stations")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "station_store_error",
            "message": "Station store could not be loaded.",
            "details": {},
            "field_errors": [],
        }
    }
