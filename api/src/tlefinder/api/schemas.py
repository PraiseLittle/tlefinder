"""Public JSON contracts for the TLE Finder HTTP API."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from math import isfinite
from numbers import Real
from typing import Any, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

SatelliteGroupValue: TypeAlias = Literal["active", "visual", "amateur"]
TleAgeLimitValue: TypeAlias = Literal["24h", "1w"]
SearchStatusValue: TypeAlias = Literal["results", "no_result"]
ApiErrorCode: TypeAlias = Literal[
    "validation_error",
    "station_validation_error",
    "station_store_error",
    "tle_unavailable",
    "tle_stale",
    "search_execution_error",
    "internal_error",
]

_EXPLICIT_OFFSET_DATETIME_RE = re.compile(r".*(?:Z|[+-]\d{2}:\d{2})$")


class ApiSchema(BaseModel):
    """Base class for public API models."""

    model_config = ConfigDict(extra="forbid")


class StationCoordinates(ApiSchema):
    """Shared latitude, longitude, and elevation fields for stations."""

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    elevation_m: float = Field(ge=-500.0, le=8000.0)

    @field_validator("latitude", "longitude", "elevation_m", mode="before")
    @classmethod
    def validate_numeric_field(cls, value: Any) -> float:
        return _require_finite_number(value)


class PersistedStation(StationCoordinates):
    """Station entry persisted in the API-controlled station list."""

    name: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: Any) -> str:
        return _trim_required_string(value, "name")


class SearchStation(StationCoordinates):
    """Station supplied for a search request."""

    name: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_optional_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _trim_required_string(value, "name")


class SearchWindow(ApiSchema):
    """Search interval supplied by an API client."""

    start_at: datetime
    duration_minutes: float = Field(gt=0.0, le=30.0)

    @field_validator("start_at", mode="before")
    @classmethod
    def validate_start_at_input(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not _EXPLICIT_OFFSET_DATETIME_RE.fullmatch(value):
                raise ValueError(
                    "start_at must be an ISO 8601 datetime with an explicit UTC offset"
                )
            try:
                normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
                return datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise ValueError("start_at must be a valid ISO 8601 datetime") from exc
        return value

    @field_validator("start_at")
    @classmethod
    def validate_start_at_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("start_at must include an explicit UTC offset")
        if not isinstance(value.tzinfo, timezone):
            raise ValueError("start_at must use UTC or a fixed UTC offset")
        return value

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def validate_duration_minutes(cls, value: Any) -> float:
        return _require_finite_number(value)


class RangeConstraint(ApiSchema):
    """Inclusive lower and upper bounds for a numeric criterion."""

    minimum: float | None = None
    maximum: float | None = None

    @field_validator("minimum", "maximum", mode="before")
    @classmethod
    def validate_optional_numeric_field(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _require_finite_number(value)

    @model_validator(mode="after")
    def validate_order(self) -> RangeConstraint:
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("minimum must not be greater than maximum")
        return self


class ApparentAltitudeRange(RangeConstraint):
    """Apparent altitude bounds in degrees."""

    @model_validator(mode="after")
    def validate_apparent_altitude_bounds(self) -> ApparentAltitudeRange:
        _validate_optional_bounds(
            "apparent altitude",
            self.minimum,
            self.maximum,
            lower=0.0,
            upper=90.0,
        )
        return self


class SunProximityRange(RangeConstraint):
    """Sun-proximity bounds in degrees."""

    @model_validator(mode="after")
    def validate_sun_proximity_bounds(self) -> SunProximityRange:
        _validate_optional_bounds(
            "sun proximity",
            self.minimum,
            self.maximum,
            lower=0.0,
            upper=180.0,
        )
        return self


class SatelliteAltitudeRange(RangeConstraint):
    """Satellite altitude bounds in kilometers."""

    @model_validator(mode="after")
    def validate_satellite_altitude_bounds(self) -> SatelliteAltitudeRange:
        _validate_optional_bounds(
            "satellite altitude",
            self.minimum,
            self.maximum,
            lower=200.0,
            upper=15000.0,
        )
        return self


class TargetToleranceConstraint(ApiSchema):
    """Target value with an allowed absolute tolerance."""

    target: float
    tolerance: float

    @field_validator("target", "tolerance", mode="before")
    @classmethod
    def validate_numeric_field(cls, value: Any) -> float:
        return _require_finite_number(value)


class ApparentAltitudeTargetTolerance(TargetToleranceConstraint):
    """Target/tolerance constraint for apparent altitude in degrees."""

    @model_validator(mode="after")
    def validate_apparent_altitude_target(self) -> ApparentAltitudeTargetTolerance:
        _validate_required_bound(
            "apparent altitude target",
            self.target,
            lower=0.0,
            upper=90.0,
        )
        _validate_required_bound(
            "apparent altitude tolerance",
            self.tolerance,
            lower=0.0,
            upper=90.0,
        )
        return self


class AzimuthTargetTolerance(TargetToleranceConstraint):
    """Target/tolerance constraint for azimuth in degrees."""

    @model_validator(mode="after")
    def validate_azimuth_target(self) -> AzimuthTargetTolerance:
        _validate_required_bound(
            "azimuth target",
            self.target,
            lower=0.0,
            upper=360.0,
            upper_inclusive=False,
        )
        _validate_required_bound(
            "azimuth tolerance",
            self.tolerance,
            lower=0.0,
            upper=180.0,
        )
        return self


class AdvancedSearchCriteria(ApiSchema):
    """Supported advanced search filters and selection controls."""

    culmination_altitude_deg: ApparentAltitudeRange | None = None
    culmination_altitude_target_deg: ApparentAltitudeTargetTolerance | None = None
    start_azimuth_deg: AzimuthTargetTolerance | None = None
    end_azimuth_deg: AzimuthTargetTolerance | None = None
    culmination_azimuth_deg: AzimuthTargetTolerance | None = None
    sun_proximity_deg: SunProximityRange | None = None
    satellite_altitude_km: SatelliteAltitudeRange | None = None
    result_limit: int | None = Field(default=None, gt=0)
    score_threshold: float | None = Field(default=None, ge=0.0, le=100.0)

    @field_validator("result_limit", mode="before")
    @classmethod
    def validate_result_limit(cls, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("result_limit must be a strictly positive integer")
        return value

    @field_validator("score_threshold", mode="before")
    @classmethod
    def validate_score_threshold(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _require_finite_number(value)


class SimpleSearchRequest(ApiSchema):
    """Simple search body with only station and window inputs."""

    station: SearchStation
    window: SearchWindow
    tle_age_limit: TleAgeLimitValue = "24h"


class AdvancedSearchRequest(ApiSchema):
    """Advanced search body with supported criteria only."""

    station: SearchStation
    window: SearchWindow
    satellite_group: SatelliteGroupValue = "active"
    tle_age_limit: TleAgeLimitValue = "24h"
    criteria: AdvancedSearchCriteria = Field(default_factory=AdvancedSearchCriteria)


class TleResponse(ApiSchema):
    """TLE data exposed in a search result."""

    name: str
    line1: str
    line2: str
    epoch_utc: datetime
    source_group: SatelliteGroupValue

    @field_validator("epoch_utc")
    @classmethod
    def validate_epoch_utc(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, "epoch_utc")

    @field_serializer("epoch_utc", when_used="json")
    def serialize_epoch_utc(self, value: datetime) -> str:
        return _serialize_utc_datetime(value)


class SatelliteResponse(ApiSchema):
    """Satellite data exposed in a search result."""

    name: str
    catalog_number: int
    tle: TleResponse


class PassGeometryResponse(ApiSchema):
    """Pass geometry exposed in a search result."""

    start_time_utc: datetime
    end_time_utc: datetime
    culmination_time_utc: datetime
    start_azimuth_deg: float
    end_azimuth_deg: float
    culmination_azimuth_deg: float
    culmination_altitude_deg: float

    @field_validator("start_time_utc", "end_time_utc", "culmination_time_utc")
    @classmethod
    def validate_utc_datetime(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value, "geometry time")

    @field_serializer(
        "start_time_utc",
        "end_time_utc",
        "culmination_time_utc",
        when_used="json",
    )
    def serialize_utc_datetime(self, value: datetime) -> str:
        return _serialize_utc_datetime(value)


class PassMetricsResponse(ApiSchema):
    """Derived pass metrics exposed in a search result."""

    satellite_altitude_km: float
    sun_proximity_deg: float | None = None


class SearchResultResponse(ApiSchema):
    """One ranked candidate pass in a search response."""

    rank: int = Field(gt=0)
    match_score: float = Field(ge=0.0, le=100.0)
    satellite: SatelliteResponse
    geometry: PassGeometryResponse
    metrics: PassMetricsResponse
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rank", mode="before")
    @classmethod
    def validate_rank(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("rank must be a strictly positive integer")
        return value

    @field_validator("match_score", mode="before")
    @classmethod
    def validate_match_score(cls, value: Any) -> float:
        return _require_finite_number(value)


class SearchResponse(ApiSchema):
    """Search response for result and no-result outcomes."""

    status: SearchStatusValue
    results: list[SearchResultResponse]
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_result_consistency(self) -> SearchResponse:
        if self.status == "no_result" and self.results:
            raise ValueError("no_result responses must not contain results")
        if self.status == "results" and not self.results:
            raise ValueError("results responses must contain at least one result")
        return self


class StationListRequest(ApiSchema):
    """Complete replacement body for the persisted station list."""

    stations: list[PersistedStation]


class StationListResponse(ApiSchema):
    """Persisted station list response."""

    stations: list[PersistedStation]


class FieldError(ApiSchema):
    """Single validation field error."""

    field: str
    message: str

    @field_validator("field", "message", mode="before")
    @classmethod
    def validate_non_empty_string(cls, value: Any) -> str:
        return _trim_required_string(value, "field error value")


class ApiError(ApiSchema):
    """Machine-readable API error body."""

    code: ApiErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    field_errors: list[FieldError] = Field(default_factory=list)

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, value: Any) -> str:
        return _trim_required_string(value, "message")


class ErrorResponse(ApiSchema):
    """Stable top-level error response envelope."""

    error: ApiError


def _trim_required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(f"{field_name} must not be empty")
    return trimmed


def _require_finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("value must be numeric")
    number = float(value)
    if not isfinite(number):
        raise ValueError("value must be finite")
    return number


def _validate_optional_bounds(
    name: str,
    minimum: float | None,
    maximum: float | None,
    *,
    lower: float,
    upper: float,
) -> None:
    if minimum is not None:
        _validate_required_bound(f"{name} minimum", minimum, lower=lower, upper=upper)
    if maximum is not None:
        _validate_required_bound(f"{name} maximum", maximum, lower=lower, upper=upper)


def _validate_required_bound(
    name: str,
    value: float,
    *,
    lower: float,
    upper: float,
    upper_inclusive: bool = True,
) -> None:
    if value < lower:
        raise ValueError(f"{name} must be at least {lower:g}")
    if upper_inclusive:
        if value > upper:
            raise ValueError(f"{name} must be at most {upper:g}")
    elif value >= upper:
        raise ValueError(f"{name} must be less than {upper:g}")


def _require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include an explicit UTC reference")
    return value


def _serialize_utc_datetime(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


__all__ = [
    "AdvancedSearchCriteria",
    "AdvancedSearchRequest",
    "ApiError",
    "ApiErrorCode",
    "ApparentAltitudeRange",
    "ApparentAltitudeTargetTolerance",
    "AzimuthTargetTolerance",
    "ErrorResponse",
    "FieldError",
    "PassGeometryResponse",
    "PassMetricsResponse",
    "PersistedStation",
    "RangeConstraint",
    "SatelliteAltitudeRange",
    "SatelliteGroupValue",
    "SatelliteResponse",
    "SearchResponse",
    "SearchResultResponse",
    "SearchStation",
    "SearchStatusValue",
    "SearchWindow",
    "SimpleSearchRequest",
    "StationListRequest",
    "StationListResponse",
    "SunProximityRange",
    "TargetToleranceConstraint",
    "TleAgeLimitValue",
    "TleResponse",
]
