import type {
  AdvancedSearchCriteria,
  AdvancedSearchRequest,
  PersistedStation,
  SimpleSearchRequest,
} from "@/api/types";
import type {
  AzimuthKey,
  RangeKey,
  SearchForm,
  SearchMode,
} from "./form";

export type StationDraft = {
  id?: string;
  name: string;
  latitude: number | string;
  longitude: number | string;
  elevation_m: number | string;
};

export interface ValidationResult<TRequest> {
  errors: Record<string, string>;
  request: TRequest | null;
}

const RANGE_BOUNDS: Record<RangeKey, { lo: number; hi: number }> = {
  culmination_altitude_deg: { lo: 0, hi: 90 },
  sun_proximity_deg: { lo: 0, hi: 180 },
  satellite_altitude_km: { lo: 200, hi: 15000 },
};

const AZIMUTH_KEYS: AzimuthKey[] = [
  "start_azimuth_deg",
  "end_azimuth_deg",
  "culmination_azimuth_deg",
];

export function validateStation(
  draft: StationDraft,
  takenNames: string[],
  existingName: string | undefined,
): { errors: Record<string, string>; payload: PersistedStation | null } {
  const errors: Record<string, string> = {};
  const name = String(draft.name).trim();
  if (!name) errors.name = "Required.";
  else if (takenNames.includes(name) && name !== existingName)
    errors.name = "A station with this name already exists.";

  const lat = parseFloat(String(draft.latitude));
  if (draft.latitude === "" || Number.isNaN(lat))
    errors.latitude = "Required, numeric.";
  else if (lat < -90 || lat > 90)
    errors.latitude = "Latitude must be between −90 and +90°.";

  const lon = parseFloat(String(draft.longitude));
  if (draft.longitude === "" || Number.isNaN(lon))
    errors.longitude = "Required, numeric.";
  else if (lon < -180 || lon > 180)
    errors.longitude = "Longitude must be between −180 and +180°.";

  const el = parseFloat(String(draft.elevation_m));
  if (draft.elevation_m === "" || Number.isNaN(el))
    errors.elevation_m = "Required, numeric.";
  else if (el < -500 || el > 8000)
    errors.elevation_m = "Elevation must be between −500 and 8000 m.";

  if (Object.keys(errors).length) return { errors, payload: null };
  return {
    errors,
    payload: { name, latitude: lat, longitude: lon, elevation_m: el },
  };
}

export function buildSearchRequest(
  mode: SearchMode,
  station: PersistedStation | null,
  form: SearchForm,
): ValidationResult<SimpleSearchRequest | AdvancedSearchRequest> {
  const errors: Record<string, string> = {};
  if (!station) {
    errors["station"] = "Select a station.";
    return { errors, request: null };
  }

  // ── Window ─────────────────────────────────────────────────
  let start_at_iso: string | null = null;
  if (form.window.tz_mode === "utc") {
    const s = (form.window.start_at_utc || "").trim();
    if (
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})$/.test(s)
    ) {
      errors["window.start_at"] =
        "ISO 8601 datetime with explicit UTC (Z) or offset required.";
    } else {
      start_at_iso = s;
    }
  } else {
    const s = (form.window.start_at_local || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(s)) {
      errors["window.start_at"] = "Local start time required.";
    } else if (!/^[+-]\d{2}:\d{2}$/.test(form.window.utc_offset)) {
      errors["window.start_at"] = "UTC offset required for local time.";
    } else {
      const withSec = s.length === 16 ? s + ":00" : s;
      start_at_iso = `${withSec}${form.window.utc_offset}`;
    }
  }

  const dur = parseFloat(form.window.duration_minutes);
  if (!Number.isFinite(dur) || dur <= 0)
    errors["window.duration_minutes"] = "Must be > 0 minutes.";
  else if (dur > 30)
    errors["window.duration_minutes"] = "Must be ≤ 30 minutes.";

  // ── Advanced criteria ──────────────────────────────────────
  const criteria: AdvancedSearchCriteria = {};
  if (mode === "advanced") {
    if (form.criteria.result_limit !== "") {
      const rl = Number(form.criteria.result_limit);
      if (!Number.isInteger(rl) || rl <= 0)
        errors["criteria.result_limit"] = "Strictly positive integer.";
      else criteria.result_limit = rl;
    }
    if (form.criteria.score_threshold !== "") {
      const st = parseFloat(form.criteria.score_threshold);
      if (!Number.isFinite(st) || st < 0 || st > 100)
        errors["criteria.score_threshold"] = "Numeric, 0–100.";
      else criteria.score_threshold = st;
    }

    for (const [key, { lo, hi }] of Object.entries(RANGE_BOUNDS) as [
      RangeKey,
      { lo: number; hi: number },
    ][]) {
      if (!form.criteria_enabled[key]) continue;
      const v = form.criteria[key];
      const obj: { minimum?: number; maximum?: number } = {};
      (["minimum", "maximum"] as const).forEach((kk) => {
        const raw = v[kk];
        if (raw === "" || raw == null) return;
        const n = parseFloat(raw);
        const errKey = `criteria.${key}.${kk === "minimum" ? "min" : "max"}`;
        if (!Number.isFinite(n)) errors[errKey] = "Numeric required.";
        else if (n < lo || n > hi)
          errors[errKey] = `Out of range [${lo}, ${hi}].`;
        else obj[kk] = n;
      });
      if (obj.minimum != null && obj.maximum != null && obj.minimum > obj.maximum) {
        errors[`criteria.${key}.order`] =
          "Minimum must not be greater than maximum.";
      }
      if (Object.keys(obj).length) {
        (criteria as Record<string, unknown>)[key] = obj;
      }
    }

    for (const key of AZIMUTH_KEYS) {
      if (!form.criteria_enabled[key]) continue;
      const v = form.criteria[key];
      const t = parseFloat(v.target);
      const tol = parseFloat(v.tolerance);
      let ok = true;
      if (!Number.isFinite(t) || t < 0 || t >= 360) {
        errors[`criteria.${key}.target`] = "0 ≤ target < 360.";
        ok = false;
      }
      if (!Number.isFinite(tol) || tol < 0 || tol > 180) {
        errors[`criteria.${key}.tol`] = "0 ≤ tolerance ≤ 180.";
        ok = false;
      }
      if (ok) (criteria as Record<string, unknown>)[key] = { target: t, tolerance: tol };
    }
  }

  if (Object.keys(errors).length || !start_at_iso) {
    return { errors, request: null };
  }

  const stationForRequest = {
    name: station.name,
    latitude: station.latitude,
    longitude: station.longitude,
    elevation_m: station.elevation_m,
  };

  if (mode === "simple") {
    const request: SimpleSearchRequest = {
      station: stationForRequest,
      window: { start_at: start_at_iso, duration_minutes: dur },
      tle_age_limit: form.tle_age_limit,
    };
    return { errors, request };
  }

  const request: AdvancedSearchRequest = {
    station: stationForRequest,
    window: { start_at: start_at_iso, duration_minutes: dur },
    satellite_group: form.satellite_group,
    tle_age_limit: form.tle_age_limit,
    criteria,
  };
  return { errors, request };
}
