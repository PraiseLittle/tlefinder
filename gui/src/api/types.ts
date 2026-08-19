/**
 * TypeScript mirror of `tlefinder.api.schemas` (Pydantic models).
 * Keep field names and value types in sync with `api/src/tlefinder/api/schemas.py`.
 */

export type SatelliteGroup = "active" | "visual" | "amateur";
export type TleAgeLimit = "24h" | "1w";
export type SearchStatus = "results" | "no_result";

export type ApiErrorCode =
  | "validation_error"
  | "station_validation_error"
  | "station_store_error"
  | "tle_unavailable"
  | "tle_stale"
  | "search_execution_error"
  | "internal_error";

// ── Station shapes ─────────────────────────────────────────────
export interface StationCoordinates {
  latitude: number;
  longitude: number;
  elevation_m: number;
}

export interface PersistedStation extends StationCoordinates {
  name: string;
}

export interface SearchStation extends StationCoordinates {
  name?: string | null;
}

export interface StationListRequest {
  stations: PersistedStation[];
}
export interface StationListResponse {
  stations: PersistedStation[];
}

// ── Window ────────────────────────────────────────────────────
export interface SearchWindow {
  /** ISO 8601 datetime with explicit UTC offset (e.g. `…Z` or `…+02:00`). */
  start_at: string;
  /** Strictly > 0 and ≤ 30. */
  duration_minutes: number;
}

// ── Constraints ───────────────────────────────────────────────
export interface RangeConstraint {
  minimum?: number | null;
  maximum?: number | null;
}
export type ApparentAltitudeRange = RangeConstraint;
export type SunProximityRange = RangeConstraint;
export type SatelliteAltitudeRange = RangeConstraint;

export interface TargetToleranceConstraint {
  target: number;
  tolerance: number;
}
export type ApparentAltitudeTargetTolerance = TargetToleranceConstraint;
export type AzimuthTargetTolerance = TargetToleranceConstraint;

// ── Advanced criteria ─────────────────────────────────────────
export interface AdvancedSearchCriteria {
  culmination_altitude_deg?: ApparentAltitudeRange | null;
  culmination_altitude_target_deg?: ApparentAltitudeTargetTolerance | null;
  start_azimuth_deg?: AzimuthTargetTolerance | null;
  end_azimuth_deg?: AzimuthTargetTolerance | null;
  culmination_azimuth_deg?: AzimuthTargetTolerance | null;
  sun_proximity_deg?: SunProximityRange | null;
  satellite_altitude_km?: SatelliteAltitudeRange | null;
  result_limit?: number | null;
  score_threshold?: number | null;
}

// ── Search requests ──────────────────────────────────────────
export interface SimpleSearchRequest {
  station: SearchStation;
  window: SearchWindow;
  tle_age_limit?: TleAgeLimit;
}
export interface AdvancedSearchRequest {
  station: SearchStation;
  window: SearchWindow;
  satellite_group?: SatelliteGroup;
  tle_age_limit?: TleAgeLimit;
  criteria?: AdvancedSearchCriteria;
}

// ── Response shapes ──────────────────────────────────────────
export interface TleResponse {
  name: string;
  line1: string;
  line2: string;
  /** ISO 8601 UTC datetime, suffixed with `Z`. */
  epoch_utc: string;
  source_group: SatelliteGroup;
}
export interface SatelliteResponse {
  name: string;
  catalog_number: number;
  tle: TleResponse;
}
export interface PassGeometryResponse {
  start_time_utc: string;
  end_time_utc: string;
  culmination_time_utc: string;
  start_azimuth_deg: number;
  end_azimuth_deg: number;
  culmination_azimuth_deg: number;
  culmination_altitude_deg: number;
}
export interface PassMetricsResponse {
  satellite_altitude_km: number;
  sun_proximity_deg?: number | null;
}
export interface SearchResultResponse {
  rank: number;
  match_score: number;
  satellite: SatelliteResponse;
  geometry: PassGeometryResponse;
  metrics: PassMetricsResponse;
  diagnostics: Record<string, unknown>;
}
export interface SearchResponse {
  status: SearchStatus;
  results: SearchResultResponse[];
  diagnostics: Record<string, unknown>;
}

// ── Error envelope ───────────────────────────────────────────
export interface FieldError {
  field: string;
  message: string;
}
export interface ApiErrorBody {
  code: ApiErrorCode;
  message: string;
  details: Record<string, unknown>;
  field_errors: FieldError[];
}
export interface ErrorResponse {
  error: ApiErrorBody;
}
