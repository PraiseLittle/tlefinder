import type {
  AdvancedSearchCriteria,
  AdvancedSearchRequest,
  SimpleSearchRequest,
  TleAgeLimit,
} from "@/api/types";

/** Form state shape — flat for easy <input/> binding. */
export type SearchMode = "simple" | "advanced";

export type RangeKey =
  | "culmination_altitude_deg"
  | "sun_proximity_deg"
  | "satellite_altitude_km";
export type AzimuthKey =
  | "start_azimuth_deg"
  | "end_azimuth_deg"
  | "culmination_azimuth_deg";

export interface SearchForm {
  satellite_group: "active" | "visual" | "amateur";
  tle_age_limit: TleAgeLimit;
  window: {
    tz_mode: "utc" | "local";
    start_at_utc: string;
    start_at_local: string;
    utc_offset: string;
    duration_minutes: string;
  };
  criteria_enabled: Record<RangeKey | AzimuthKey, boolean>;
  criteria: {
    result_limit: string;
    score_threshold: string;
    culmination_altitude_deg: { minimum: string; maximum: string };
    sun_proximity_deg: { minimum: string; maximum: string };
    satellite_altitude_km: { minimum: string; maximum: string };
    start_azimuth_deg: { target: string; tolerance: string };
    end_azimuth_deg: { target: string; tolerance: string };
    culmination_azimuth_deg: { target: string; tolerance: string };
  };
}

export function makeInitialForm(): SearchForm {
  // Default start = nearest top of next hour, UTC
  const now = new Date();
  const next = new Date(Math.ceil(now.getTime() / 3_600_000) * 3_600_000);
  const isoUtc = next.toISOString().replace(/\.\d{3}Z$/, "Z");
  const pad = (n: number) => String(n).padStart(2, "0");
  const local =
    `${next.getUTCFullYear()}-${pad(next.getUTCMonth() + 1)}-` +
    `${pad(next.getUTCDate())}T${pad(next.getUTCHours())}:${pad(next.getUTCMinutes())}:00`;
  return {
    satellite_group: "active",
    tle_age_limit: "24h",
    window: {
      tz_mode: "utc",
      start_at_utc: isoUtc,
      start_at_local: local,
      utc_offset: "+02:00",
      duration_minutes: "15",
    },
    criteria_enabled: {
      culmination_altitude_deg: false,
      sun_proximity_deg: false,
      satellite_altitude_km: false,
      start_azimuth_deg: false,
      end_azimuth_deg: false,
      culmination_azimuth_deg: false,
    },
    criteria: {
      result_limit: "",
      score_threshold: "",
      culmination_altitude_deg: { minimum: "", maximum: "" },
      sun_proximity_deg: { minimum: "", maximum: "" },
      satellite_altitude_km: { minimum: "", maximum: "" },
      start_azimuth_deg: { target: "", tolerance: "" },
      end_azimuth_deg: { target: "", tolerance: "" },
      culmination_azimuth_deg: { target: "", tolerance: "" },
    },
  };
}

/** Re-exports the request types for convenience. */
export type {
  SimpleSearchRequest,
  AdvancedSearchRequest,
  AdvancedSearchCriteria,
};
