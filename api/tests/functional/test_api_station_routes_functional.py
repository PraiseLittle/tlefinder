from __future__ import annotations

import pytest
import yaml


pytestmark = pytest.mark.functional


def test_get_stations_creates_empty_list_with_missing_store(api_client_factory):
    client, store_path = api_client_factory()

    assert not store_path.exists()

    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    assert response.json() == {"stations": []}
    assert yaml.safe_load(store_path.read_text(encoding="utf-8")) == {"stations": []}


def test_put_stations_persists_valid_list_and_later_get_returns_it(
    api_client_factory,
    station_payload,
):
    client, _store_path = api_client_factory()
    stations = [
        station_payload(),
        station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503),
    ]

    put_response = client.put("/api/v1/stations", json={"stations": stations})
    get_response = client.get("/api/v1/stations")

    assert put_response.status_code == 200
    assert put_response.json() == {"stations": stations}
    assert get_response.status_code == 200
    assert get_response.json() == {"stations": stations}


def test_invalid_station_update_returns_422_and_preserves_previous_store(
    api_client_factory,
    station_payload,
):
    client, store_path = api_client_factory()
    existing_station = station_payload()

    first_response = client.put(
        "/api/v1/stations",
        json={"stations": [existing_station]},
    )
    previous_store_text = store_path.read_text(encoding="utf-8")

    response = client.put(
        "/api/v1/stations",
        json={
            "stations": [
                station_payload(name="Paris A"),
                station_payload(name="Paris B"),
            ]
        },
    )

    assert first_response.status_code == 200
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "station_validation_error"
    assert response.json()["error"]["field_errors"][0]["field"] == "stations.1"
    assert store_path.read_text(encoding="utf-8") == previous_store_text
    assert client.get("/api/v1/stations").json() == {"stations": [existing_station]}


def test_malformed_persisted_yaml_returns_machine_readable_store_error(
    api_client_factory,
):
    client, store_path = api_client_factory()
    store_path.write_text("stations: [\n", encoding="utf-8")

    response = client.get("/api/v1/stations")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "station_store_error"
    assert response.json()["error"]["message"] == "Station store could not be loaded."


def test_api_settings_keep_station_store_paths_isolated(
    api_client_factory,
    tmp_path,
    station_payload,
):
    store_path_a = tmp_path / "client-a" / "stations.yaml"
    store_path_b = tmp_path / "client-b" / "stations.yaml"
    client_a, _ = api_client_factory(station_store_path=store_path_a)
    client_b, _ = api_client_factory(station_store_path=store_path_b)
    station_a = station_payload(name="Paris Observatory")
    station_b = station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503)

    response_a = client_a.put("/api/v1/stations", json={"stations": [station_a]})
    response_b_before_put = client_b.get("/api/v1/stations")
    response_b = client_b.put("/api/v1/stations", json={"stations": [station_b]})

    assert response_a.status_code == 200
    assert response_b_before_put.status_code == 200
    assert response_b_before_put.json() == {"stations": []}
    assert response_b.status_code == 200
    assert client_a.get("/api/v1/stations").json() == {"stations": [station_a]}
    assert client_b.get("/api/v1/stations").json() == {"stations": [station_b]}
    assert store_path_a.read_text(encoding="utf-8") != store_path_b.read_text(
        encoding="utf-8"
    )
