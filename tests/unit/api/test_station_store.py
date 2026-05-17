from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml


def station_payload(**overrides):
    payload = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    payload.update(overrides)
    return payload


def write_station_file(path: Path, stations: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"stations": stations}, sort_keys=False), encoding="utf-8")


def read_station_file(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_first_access_creates_parent_directories_and_empty_yaml_station_list(tmp_path):
    from tlefinder.api.station_store import load_stations

    station_store_path = tmp_path / "nested" / "config" / "stations.yaml"

    stations = load_stations(station_store_path)

    assert stations == []
    assert station_store_path.exists()
    assert read_station_file(station_store_path) == {"stations": []}


def test_existing_valid_yaml_file_is_loaded_into_station_schemas(tmp_path):
    from tlefinder.api.schemas import PersistedStation
    from tlefinder.api.station_store import load_stations

    station_store_path = tmp_path / "stations.yaml"
    write_station_file(
        station_store_path,
        [
            station_payload(),
            station_payload(
                name="Tokyo",
                latitude=35.6762,
                longitude=139.6503,
                elevation_m=40.0,
            ),
        ],
    )

    stations = load_stations(station_store_path)

    assert [type(station) for station in stations] == [PersistedStation, PersistedStation]
    assert [station.name for station in stations] == ["Paris Observatory", "Tokyo"]
    assert stations[0].latitude == 48.8367


def test_malformed_yaml_returns_station_store_error_without_parser_details(tmp_path):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.station_store import load_stations

    station_store_path = tmp_path / "stations.yaml"
    station_store_path.write_text("stations: [", encoding="utf-8")

    with pytest.raises(StationStoreError) as exc_info:
        load_stations(station_store_path)

    assert exc_info.value.code == "station_store_error"
    assert "could not be loaded" in exc_info.value.message
    assert "while parsing" not in exc_info.value.message
    assert "ParserError" not in exc_info.value.message


def test_missing_required_yaml_fields_return_machine_readable_store_error(tmp_path):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.station_store import load_stations

    station_store_path = tmp_path / "stations.yaml"
    write_station_file(
        station_store_path,
        [{"latitude": 48.8367, "longitude": 2.3365, "elevation_m": 67.0}],
    )

    with pytest.raises(StationStoreError) as exc_info:
        load_stations(station_store_path)

    assert exc_info.value.code == "station_store_error"
    assert exc_info.value.field_errors
    assert exc_info.value.field_errors[0].field == "stations.0.name"


def test_core_package_does_not_read_or_write_the_station_yaml_file(monkeypatch, tmp_path):
    from tlefinder.api.config import STATION_STORE_PATH_ENV
    from tlefinder.core import (
        GroundStation,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
        SearchWindow,
        validate_search_request,
    )

    station_store_path = tmp_path / "core-must-not-touch" / "stations.yaml"
    monkeypatch.setenv(STATION_STORE_PATH_ENV, str(station_store_path))

    validate_search_request(
        SearchRequest(
            station=GroundStation(latitude=48.8367, longitude=2.3365, elevation_m=67.0),
            window=SearchWindow(
                start_at=datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
                duration_minutes=10,
            ),
            criteria=SearchCriteria(),
            satellite_group=SatelliteGroup.ACTIVE,
        )
    )

    assert not station_store_path.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("name", "", id="empty-name"),
        pytest.param("name", "   ", id="blank-name"),
        pytest.param("name", None, id="missing-name"),
        pytest.param("latitude", -90.1, id="latitude-too-low"),
        pytest.param("latitude", 90.1, id="latitude-too-high"),
        pytest.param("latitude", True, id="latitude-bool"),
        pytest.param("longitude", -180.1, id="longitude-too-low"),
        pytest.param("longitude", 180.1, id="longitude-too-high"),
        pytest.param("longitude", False, id="longitude-bool"),
        pytest.param("elevation_m", -500.1, id="elevation-too-low"),
        pytest.param("elevation_m", 8000.1, id="elevation-too-high"),
        pytest.param("elevation_m", True, id="elevation-bool"),
    ],
)
def test_replace_stations_rejects_invalid_latitude_longitude_elevation_and_names(
    field,
    value,
    tmp_path,
):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"
    invalid_station = station_payload(**{field: value})

    with pytest.raises(StationValidationError) as exc_info:
        replace_stations(station_store_path, [invalid_station])

    assert exc_info.value.code == "station_validation_error"
    assert exc_info.value.field_errors
    assert exc_info.value.field_errors[0].field.startswith("stations.0")


def test_replace_stations_rejects_duplicate_physical_stations(tmp_path):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"

    with pytest.raises(StationValidationError) as exc_info:
        replace_stations(
            station_store_path,
            [
                station_payload(name="Paris A"),
                station_payload(name="Paris B"),
            ],
        )

    assert exc_info.value.code == "station_validation_error"
    assert exc_info.value.field_errors[0].field == "stations.1"
    assert "physical station" in exc_info.value.field_errors[0].message


def test_replace_stations_rejects_duplicate_names_with_different_coordinates(tmp_path):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"

    with pytest.raises(StationValidationError) as exc_info:
        replace_stations(
            station_store_path,
            [
                station_payload(name="Paris Observatory"),
                station_payload(
                    name="Paris Observatory",
                    latitude=35.6762,
                    longitude=139.6503,
                    elevation_m=40.0,
                ),
            ],
        )

    assert exc_info.value.field_errors[0].field == "stations.1.name"
    assert "different coordinates" in exc_info.value.field_errors[0].message


def test_duplicate_detection_normalizes_all_coordinates_to_first_five_decimal_digits(
    tmp_path,
):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"

    with pytest.raises(StationValidationError):
        replace_stations(
            station_store_path,
            [
                station_payload(
                    name="Station A",
                    latitude=48.836789,
                    longitude=2.336549,
                    elevation_m=67.123459,
                ),
                station_payload(
                    name="Station B",
                    latitude=48.836781,
                    longitude=2.336541,
                    elevation_m=67.123451,
                ),
            ],
        )


@pytest.mark.parametrize(
    ("first_latitude", "second_latitude"),
    [
        pytest.param(1.234569, 1.234561, id="positive-truncation"),
        pytest.param(-1.234569, -1.234561, id="negative-truncation"),
    ],
)
def test_duplicate_detection_truncates_coordinates_toward_zero(
    first_latitude,
    second_latitude,
    tmp_path,
):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"

    with pytest.raises(StationValidationError):
        replace_stations(
            station_store_path,
            [
                station_payload(name="Station A", latitude=first_latitude),
                station_payload(name="Station B", latitude=second_latitude),
            ],
        )


def test_load_rejects_persisted_list_with_more_than_one_name_for_same_station(tmp_path):
    from tlefinder.api.errors import StationStoreError
    from tlefinder.api.station_store import load_stations

    station_store_path = tmp_path / "stations.yaml"
    write_station_file(
        station_store_path,
        [
            station_payload(name="Paris A"),
            station_payload(name="Paris B"),
        ],
    )

    with pytest.raises(StationStoreError) as exc_info:
        load_stations(station_store_path)

    assert exc_info.value.code == "station_store_error"
    assert exc_info.value.field_errors[0].field == "stations.1"


def test_replace_stations_writes_the_submitted_list(tmp_path):
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"
    submitted_stations = [
        station_payload(),
        station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503),
    ]

    stations = replace_stations(station_store_path, submitted_stations)

    assert [station.name for station in stations] == ["Paris Observatory", "Tokyo"]
    assert read_station_file(station_store_path) == {"stations": submitted_stations}


def test_invalid_replacement_preserves_previous_persisted_file(tmp_path):
    from tlefinder.api.errors import StationValidationError
    from tlefinder.api.station_store import replace_stations

    station_store_path = tmp_path / "stations.yaml"
    previous_stations = [station_payload()]
    write_station_file(station_store_path, previous_stations)
    previous_text = station_store_path.read_text(encoding="utf-8")

    with pytest.raises(StationValidationError):
        replace_stations(station_store_path, [station_payload(name="")])

    assert station_store_path.read_text(encoding="utf-8") == previous_text
    assert read_station_file(station_store_path) == {"stations": previous_stations}


def test_write_failures_preserve_previous_persisted_file(monkeypatch, tmp_path):
    from tlefinder.api import station_store
    from tlefinder.api.errors import StationStoreError

    station_store_path = tmp_path / "stations.yaml"
    previous_stations = [station_payload()]
    write_station_file(station_store_path, previous_stations)
    previous_text = station_store_path.read_text(encoding="utf-8")

    def fail_replace(source, target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(station_store.os, "replace", fail_replace)

    with pytest.raises(StationStoreError) as exc_info:
        station_store.replace_stations(
            station_store_path,
            [station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503)],
        )

    assert exc_info.value.code == "station_store_error"
    assert station_store_path.read_text(encoding="utf-8") == previous_text
    assert read_station_file(station_store_path) == {"stations": previous_stations}


def test_atomic_replacement_uses_temporary_file_in_same_directory(monkeypatch, tmp_path):
    from tlefinder.api import station_store

    station_store_path = tmp_path / "stations.yaml"
    replace_calls: list[tuple[Path, Path]] = []
    real_replace = station_store.os.replace

    def record_replace(source, target):
        replace_calls.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(station_store.os, "replace", record_replace)

    station_store.replace_stations(station_store_path, [station_payload()])

    assert len(replace_calls) == 1
    source, target = replace_calls[0]
    assert source.parent == station_store_path.parent
    assert source != station_store_path
    assert target == station_store_path


def test_temporary_files_are_cleaned_up_after_write_failures(monkeypatch, tmp_path):
    from tlefinder.api import station_store
    from tlefinder.api.errors import StationStoreError

    station_store_path = tmp_path / "stations.yaml"
    write_station_file(station_store_path, [station_payload()])

    def fail_replace(source, target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(station_store.os, "replace", fail_replace)

    with pytest.raises(StationStoreError):
        station_store.replace_stations(
            station_store_path,
            [station_payload(name="Tokyo", latitude=35.6762, longitude=139.6503)],
        )

    assert sorted(path.name for path in station_store_path.parent.iterdir()) == [
        "stations.yaml"
    ]


def test_unnamed_search_station_is_not_persisted(tmp_path):
    from tlefinder.api.schemas import SearchStation
    from tlefinder.api.station_store import add_station_if_new, load_stations

    station_store_path = tmp_path / "stations.yaml"

    stations = add_station_if_new(
        station_store_path,
        SearchStation(latitude=48.8367, longitude=2.3365, elevation_m=67.0),
    )

    assert stations == []
    assert load_stations(station_store_path) == []


def test_new_named_search_station_is_appended_when_route_requests_persistence(tmp_path):
    from tlefinder.api.schemas import SearchStation
    from tlefinder.api.station_store import add_station_if_new

    station_store_path = tmp_path / "stations.yaml"

    stations = add_station_if_new(
        station_store_path,
        SearchStation(
            name="Paris Observatory",
            latitude=48.8367,
            longitude=2.3365,
            elevation_m=67.0,
        ),
    )

    assert [station.name for station in stations] == ["Paris Observatory"]
    assert read_station_file(station_store_path) == {"stations": [station_payload()]}


def test_equivalent_search_station_coordinates_preserve_existing_station_name(tmp_path):
    from tlefinder.api.schemas import SearchStation
    from tlefinder.api.station_store import add_station_if_new

    station_store_path = tmp_path / "stations.yaml"
    write_station_file(station_store_path, [station_payload(name="Existing Name")])

    stations = add_station_if_new(
        station_store_path,
        SearchStation(
            name="Submitted Name",
            latitude=48.836709,
            longitude=2.336509,
            elevation_m=67.000009,
        ),
    )

    assert [station.name for station in stations] == ["Existing Name"]
    assert read_station_file(station_store_path) == {
        "stations": [station_payload(name="Existing Name")]
    }


def test_exact_duplicate_search_station_is_not_appended_twice(tmp_path):
    from tlefinder.api.schemas import SearchStation
    from tlefinder.api.station_store import add_station_if_new

    station_store_path = tmp_path / "stations.yaml"

    for _ in range(2):
        stations = add_station_if_new(
            station_store_path,
            SearchStation(
                name="Paris Observatory",
                latitude=48.8367,
                longitude=2.3365,
                elevation_m=67.0,
            ),
        )

    assert [station.name for station in stations] == ["Paris Observatory"]
    assert read_station_file(station_store_path) == {"stations": [station_payload()]}
