"""Shared domain contract for the TLE Finder core.

Diagnostics are represented as JSON-friendly dictionaries keyed by stable,
snake_case strings. Core modules should prefer values that adapters can expose
directly, such as strings, numbers, booleans, lists, and nested dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

Diagnostics: TypeAlias = dict[str, Any]
Metadata: TypeAlias = dict[str, Any]


class SatelliteGroup(str, Enum):
    """Supported TLE source groupings."""

    ACTIVE = "active"
    VISUAL = "visual"
    AMATEUR = "amateur"


class TleAgeLimit(str, Enum):
    """Supported maximum ages for TLE record epochs."""

    HOURS_24 = "24h"
    WEEK_1 = "1w"


class SearchStatus(str, Enum):
    """High-level outcome of a valid search execution."""

    RESULTS = "results"
    NO_RESULT = "no_result"


@dataclass(slots=True)
class GroundStation:
    """Optical observing site."""

    latitude: float
    longitude: float
    elevation_m: float


@dataclass(slots=True)
class SearchWindow:
    """Requested search interval before UTC normalization."""

    start_at: datetime
    duration_minutes: float


@dataclass(slots=True)
class RangeConstraint:
    """Inclusive lower and upper bounds for a numeric criterion."""

    minimum: float | None = None
    maximum: float | None = None


@dataclass(slots=True)
class TargetToleranceConstraint:
    """Target value with an allowed absolute tolerance."""

    target: float
    tolerance: float


@dataclass(slots=True)
class SearchCriteria:
    """Phase 2 search constraints and ranking controls.

    Object-type criteria are intentionally absent from this active contract.
    """

    culmination_altitude_deg: RangeConstraint | None = None
    culmination_altitude_target_deg: TargetToleranceConstraint | None = None
    start_azimuth_deg: TargetToleranceConstraint | None = None
    end_azimuth_deg: TargetToleranceConstraint | None = None
    culmination_azimuth_deg: TargetToleranceConstraint | None = None
    sun_proximity_deg: RangeConstraint | None = None
    satellite_altitude_km: RangeConstraint | None = None
    score_threshold: float = 0.0
    result_limit: int = 10


@dataclass(slots=True)
class SearchRequest:
    """Complete request passed to the reusable core engine."""

    station: GroundStation
    window: SearchWindow
    criteria: SearchCriteria
    satellite_group: SatelliteGroup
    tle_age_limit: TleAgeLimit = TleAgeLimit.HOURS_24


@dataclass(slots=True)
class TleRecord:
    """Raw two-line element record with source metadata."""

    name: str
    line1: str
    line2: str
    catalog_number: int
    epoch_utc: datetime
    source_group: SatelliteGroup
    source_path: Path


@dataclass(slots=True)
class SatelliteRecord:
    """Satellite-level data that is independent of a specific pass."""

    tle: TleRecord
    aliases: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class PassGeometry:
    """Geometric facts extracted for one candidate pass."""

    start_time_utc: datetime
    end_time_utc: datetime
    culmination_time_utc: datetime
    start_azimuth_deg: float
    end_azimuth_deg: float
    culmination_azimuth_deg: float
    culmination_altitude_deg: float


@dataclass(slots=True)
class PassMetrics:
    """Derived pass-level values used by filtering and scoring."""

    satellite_altitude_km: float | None = None
    sun_proximity_deg: float | None = None


@dataclass(slots=True)
class CandidatePass:
    """Detected pass plus scoring and ranking annotations."""

    satellite: SatelliteRecord
    geometry: PassGeometry
    metrics: PassMetrics
    match_score: float | None = None
    rank: int | None = None
    diagnostics: Diagnostics = field(default_factory=dict)


@dataclass(slots=True)
class SearchResponse:
    """Shared response model returned by GUI, API, and Python adapters."""

    results: list[CandidatePass]
    status: SearchStatus
    diagnostics: Diagnostics = field(default_factory=dict)


__all__ = [
    "CandidatePass",
    "Diagnostics",
    "GroundStation",
    "Metadata",
    "PassGeometry",
    "PassMetrics",
    "RangeConstraint",
    "SatelliteGroup",
    "SatelliteRecord",
    "SearchCriteria",
    "SearchRequest",
    "SearchResponse",
    "SearchStatus",
    "SearchWindow",
    "TargetToleranceConstraint",
    "TleAgeLimit",
    "TleRecord",
]
