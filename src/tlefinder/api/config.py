"""Runtime configuration for the TLE Finder API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

STATION_STORE_PATH_ENV = "TLEFINDER_STATION_STORE_PATH"


@dataclass(slots=True)
class ApiSettings:
    """Resolved API runtime settings."""

    station_store_path: Path


def default_station_store_path() -> Path:
    """Return the backend-controlled default YAML station store path."""
    return Path(__file__).resolve().parents[1] / "data" / "stations.yaml"


def resolve_api_settings() -> ApiSettings:
    """Resolve API settings from the environment and documented defaults."""
    configured_station_store = os.environ.get(STATION_STORE_PATH_ENV)
    station_store_path = (
        Path(configured_station_store).expanduser()
        if configured_station_store
        else default_station_store_path()
    )
    return ApiSettings(station_store_path=station_store_path)


__all__ = [
    "ApiSettings",
    "STATION_STORE_PATH_ENV",
    "default_station_store_path",
    "resolve_api_settings",
]
