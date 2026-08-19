"""Runtime configuration for the TLE Finder API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from tlefinder.core import pass_analysis

STATION_STORE_PATH_ENV = "TLEFINDER_STATION_STORE_PATH"
PARALLEL_SEARCH_ENABLED_ENV = "TLEFINDER_PARALLEL_SEARCH_ENABLED"
PARALLEL_WORKER_COUNT_ENV = "TLEFINDER_PARALLEL_WORKER_COUNT"
PARALLEL_CHUNK_SIZE_ENV = "TLEFINDER_PARALLEL_CHUNK_SIZE"
DEFAULT_PARALLEL_WORKER_COUNT = pass_analysis.DEFAULT_PARALLEL_WORKER_COUNT


@dataclass(slots=True)
class ApiSettings:
    """Resolved API runtime settings."""

    station_store_path: Path
    parallel_search_enabled: bool = False
    parallel_worker_count: int = DEFAULT_PARALLEL_WORKER_COUNT
    parallel_chunk_size: int = pass_analysis.DEFAULT_PARALLEL_CHUNK_SIZE

    def __post_init__(self) -> None:
        pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=self.parallel_worker_count,
            chunk_size=self.parallel_chunk_size,
        )


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
    return ApiSettings(
        station_store_path=station_store_path,
        parallel_search_enabled=_environment_bool(
            PARALLEL_SEARCH_ENABLED_ENV,
            default=False,
        ),
        parallel_worker_count=_environment_int(
            PARALLEL_WORKER_COUNT_ENV,
            default=DEFAULT_PARALLEL_WORKER_COUNT,
        ),
        parallel_chunk_size=_environment_int(
            PARALLEL_CHUNK_SIZE_ENV,
            default=pass_analysis.DEFAULT_PARALLEL_CHUNK_SIZE,
        ),
    )


def _environment_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _environment_int(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


__all__ = [
    "ApiSettings",
    "DEFAULT_PARALLEL_WORKER_COUNT",
    "PARALLEL_CHUNK_SIZE_ENV",
    "PARALLEL_SEARCH_ENABLED_ENV",
    "PARALLEL_WORKER_COUNT_ENV",
    "STATION_STORE_PATH_ENV",
    "default_station_store_path",
    "resolve_api_settings",
]
