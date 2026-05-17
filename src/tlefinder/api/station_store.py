"""YAML-backed station persistence boundary for the API layer."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Mapping
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, TypeAlias

import yaml
from pydantic import ValidationError as PydanticValidationError

from tlefinder.api.errors import (
    ApiErrorException,
    ApiFieldError,
    StationStoreError,
    StationValidationError,
)
from tlefinder.api.schemas import PersistedStation, SearchStation

StationInput: TypeAlias = PersistedStation | Mapping[str, Any]
SearchStationInput: TypeAlias = SearchStation | Mapping[str, Any]
PhysicalStationKey: TypeAlias = tuple[int, int, int]

_EMPTY_STATION_STORE = {"stations": []}
_NORMALIZATION_SCALE = Decimal("100000")


def ensure_store_exists(station_store_path: Path) -> None:
    """Create the YAML station store with an empty station list when absent."""
    path = Path(station_store_path)
    if path.exists():
        return

    try:
        _write_station_file(path, [])
    except StationStoreError as exc:
        raise StationStoreError(
            "Station store could not be created.",
            details={"path": str(path)},
        ) from exc


def load_stations(station_store_path: Path) -> list[PersistedStation]:
    """Load and validate the complete persisted station list."""
    path = Path(station_store_path)
    ensure_store_exists(path)
    raw_store = _load_yaml_store(path)
    station_items = _extract_station_items(
        raw_store,
        error_cls=StationStoreError,
        message="Station store could not be loaded.",
    )
    stations = _coerce_persisted_stations(
        station_items,
        error_cls=StationStoreError,
        message="Station store could not be loaded.",
    )
    _validate_unique_stations(
        stations,
        error_cls=StationStoreError,
        message="Station store could not be loaded.",
    )
    return stations


def replace_stations(
    station_store_path: Path,
    stations: Iterable[StationInput],
) -> list[PersistedStation]:
    """Validate and atomically replace the complete persisted station list."""
    path = Path(station_store_path)
    validated_stations = _validate_replacement_list(stations)
    _write_station_file(path, validated_stations)
    return validated_stations


def add_station_if_new(
    station_store_path: Path,
    station: SearchStationInput,
) -> list[PersistedStation]:
    """Append a named search station unless its physical site already exists."""
    search_station = _coerce_search_station(station)
    existing_stations = load_stations(station_store_path)

    if search_station.name is None:
        return existing_stations

    submitted_station = PersistedStation(
        name=search_station.name,
        latitude=search_station.latitude,
        longitude=search_station.longitude,
        elevation_m=search_station.elevation_m,
    )
    submitted_key = _physical_station_key(submitted_station)

    for existing_station in existing_stations:
        if _physical_station_key(existing_station) == submitted_key:
            return existing_stations

    return replace_stations(station_store_path, [*existing_stations, submitted_station])


def _load_yaml_store(path: Path) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as station_file:
            raw_store = yaml.safe_load(station_file)
    except yaml.YAMLError as exc:
        raise StationStoreError(
            "Station store could not be loaded.",
            details={"path": str(path)},
        ) from exc
    except OSError as exc:
        raise StationStoreError(
            "Station store could not be loaded.",
            details={"path": str(path)},
        ) from exc

    if not isinstance(raw_store, Mapping):
        raise StationStoreError(
            "Station store could not be loaded.",
            details={"path": str(path)},
            field_errors=[
                ApiFieldError(
                    field="stations",
                    message="station store must contain a stations list",
                )
            ],
        )
    return raw_store


def _extract_station_items(
    raw_store: Mapping[str, Any],
    *,
    error_cls: type[ApiErrorException],
    message: str,
) -> list[Any]:
    station_items = raw_store.get("stations")
    if not isinstance(station_items, list):
        raise error_cls(
            message,
            field_errors=[
                ApiFieldError(field="stations", message="stations must be a list")
            ],
        )
    return station_items


def _validate_replacement_list(
    stations: Iterable[StationInput],
) -> list[PersistedStation]:
    if isinstance(stations, (str, bytes)) or not isinstance(stations, Iterable):
        raise StationValidationError(
            field_errors=[
                ApiFieldError(field="stations", message="stations must be a list")
            ]
        )

    station_items = list(stations)
    validated_stations = _coerce_persisted_stations(
        station_items,
        error_cls=StationValidationError,
        message="Station list validation failed.",
    )
    _validate_unique_stations(
        validated_stations,
        error_cls=StationValidationError,
        message="Station list validation failed.",
    )
    return validated_stations


def _coerce_persisted_stations(
    station_items: list[Any],
    *,
    error_cls: type[ApiErrorException],
    message: str,
) -> list[PersistedStation]:
    stations: list[PersistedStation] = []
    field_errors: list[ApiFieldError] = []

    for index, item in enumerate(station_items):
        try:
            stations.append(PersistedStation.model_validate(item))
        except PydanticValidationError as exc:
            field_errors.extend(_pydantic_field_errors(exc, prefix=f"stations.{index}"))

    if field_errors:
        raise error_cls(message, field_errors=field_errors)

    return stations


def _coerce_search_station(station: SearchStationInput) -> SearchStation:
    try:
        return SearchStation.model_validate(station)
    except PydanticValidationError as exc:
        raise StationValidationError(
            field_errors=_pydantic_field_errors(exc, prefix="station")
        ) from exc


def _pydantic_field_errors(
    exc: PydanticValidationError,
    *,
    prefix: str,
) -> list[ApiFieldError]:
    field_errors: list[ApiFieldError] = []
    for error in exc.errors():
        location = error.get("loc", ())
        suffix = ".".join(str(part) for part in location)
        field = f"{prefix}.{suffix}" if suffix else prefix
        message = str(error.get("msg") or "invalid value")
        field_errors.append(ApiFieldError(field=field, message=message))
    return field_errors


def _validate_unique_stations(
    stations: list[PersistedStation],
    *,
    error_cls: type[ApiErrorException],
    message: str,
) -> None:
    name_to_key: dict[str, PhysicalStationKey] = {}
    key_to_index: dict[PhysicalStationKey, int] = {}
    field_errors: list[ApiFieldError] = []

    for index, station in enumerate(stations):
        station_key = _physical_station_key(station)

        previous_index = key_to_index.get(station_key)
        if previous_index is not None:
            field_errors.append(
                ApiFieldError(
                    field=f"stations.{index}",
                    message=(
                        "duplicate physical station matches "
                        f"stations.{previous_index}"
                    ),
                )
            )
        else:
            key_to_index[station_key] = index

        previous_key = name_to_key.get(station.name)
        if previous_key is not None and previous_key != station_key:
            field_errors.append(
                ApiFieldError(
                    field=f"stations.{index}.name",
                    message="station name is already used with different coordinates",
                )
            )
        else:
            name_to_key[station.name] = station_key

    if field_errors:
        raise error_cls(message, field_errors=field_errors)


def _physical_station_key(station: PersistedStation | SearchStation) -> PhysicalStationKey:
    return (
        _truncate_toward_zero_to_five_decimal_digits(station.latitude),
        _truncate_toward_zero_to_five_decimal_digits(station.longitude),
        _truncate_toward_zero_to_five_decimal_digits(station.elevation_m),
    )


def _truncate_toward_zero_to_five_decimal_digits(value: float) -> int:
    scaled_value = Decimal(str(value)) * _NORMALIZATION_SCALE
    return int(scaled_value.to_integral_value(rounding=ROUND_DOWN))


def _write_station_file(path: Path, stations: list[PersistedStation]) -> None:
    path = Path(path)
    payload = {
        "stations": [
            station.model_dump(mode="json")
            for station in stations
        ]
    }
    station_yaml = yaml.safe_dump(payload, sort_keys=False)
    temporary_path: Path | None = None

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(station_yaml)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
    except OSError as exc:
        _remove_temporary_file(temporary_path)
        raise StationStoreError(
            "Station store could not be saved.",
            details={"path": str(path)},
        ) from exc


def _remove_temporary_file(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


__all__ = [
    "add_station_if_new",
    "ensure_store_exists",
    "load_stations",
    "replace_stations",
]
