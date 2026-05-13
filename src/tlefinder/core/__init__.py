"""Import-safe core search package for TLE Finder."""

from __future__ import annotations

from tlefinder.core.errors import (
    PropagationError,
    SearchExecutionError,
    TleFinderError,
    TleFreshnessError,
    TleLoadError,
    ValidationError,
)
from tlefinder.core.models import (
    CandidatePass,
    Diagnostics,
    GroundStation,
    Metadata,
    PassGeometry,
    PassMetrics,
    RangeConstraint,
    SatelliteGroup,
    SatelliteRecord,
    SearchCriteria,
    SearchRequest,
    SearchResponse,
    SearchStatus,
    SearchWindow,
    TargetToleranceConstraint,
    TleRecord,
)
from tlefinder.core.time_utils import (
    build_search_interval,
    normalize_start_time_to_utc,
)
from tlefinder.core.validation import (
    validate_ground_station,
    validate_search_criteria,
    validate_search_request,
    validate_search_window,
)

__all__ = [
    "CandidatePass",
    "Diagnostics",
    "GroundStation",
    "Metadata",
    "PassGeometry",
    "PassMetrics",
    "PropagationError",
    "RangeConstraint",
    "SatelliteGroup",
    "SatelliteRecord",
    "SearchCriteria",
    "SearchExecutionError",
    "SearchRequest",
    "SearchResponse",
    "SearchStatus",
    "SearchWindow",
    "TargetToleranceConstraint",
    "TleFinderError",
    "TleFreshnessError",
    "TleLoadError",
    "TleRecord",
    "ValidationError",
    "build_search_interval",
    "normalize_start_time_to_utc",
    "validate_ground_station",
    "validate_search_criteria",
    "validate_search_request",
    "validate_search_window",
]
