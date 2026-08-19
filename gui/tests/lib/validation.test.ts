import { describe, expect, it } from "vitest";

import type { PersistedStation } from "@/api/types";
import { makeInitialForm } from "@/lib/form";
import { buildSearchRequest, validateStation } from "@/lib/validation";


const station: PersistedStation = {
  name: "Paris Observatory",
  latitude: 48.8367,
  longitude: 2.3365,
  elevation_m: 67,
};


describe("GUI validation helpers", () => {
  it("builds the exact simple-search HTTP payload", () => {
    const form = makeInitialForm();
    form.window.start_at_utc = "2026-05-12T20:00:00Z";
    form.window.duration_minutes = "10";
    form.tle_age_limit = "24h";

    expect(buildSearchRequest("simple", station, form)).toEqual({
      errors: {},
      request: {
        station,
        window: {
          start_at: "2026-05-12T20:00:00Z",
          duration_minutes: 10,
        },
        tle_age_limit: "24h",
      },
    });
  });

  it("validates station coordinate and name constraints before the API call", () => {
    const result = validateStation(
      { name: "Paris", latitude: 91, longitude: 2.3, elevation_m: 35 },
      ["Paris"],
      undefined,
    );

    expect(result.payload).toBeNull();
    expect(result.errors).toMatchObject({
      name: "A station with this name already exists.",
      latitude: "Latitude must be between −90 and +90°.",
    });
  });

  it("rejects advanced ranges whose minimum exceeds their maximum", () => {
    const form = makeInitialForm();
    form.window.start_at_utc = "2026-05-12T20:00:00Z";
    form.criteria_enabled.culmination_altitude_deg = true;
    form.criteria.culmination_altitude_deg = { minimum: "80", maximum: "20" };

    const result = buildSearchRequest("advanced", station, form);
    expect(result.request).toBeNull();
    expect(result.errors["criteria.culmination_altitude_deg.order"]).toBe(
      "Minimum must not be greater than maximum.",
    );
  });
});

