import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/api/client";
import type { SimpleSearchRequest } from "@/api/types";


const request: SimpleSearchRequest = {
  station: {
    name: "Paris Observatory",
    latitude: 48.8367,
    longitude: 2.3365,
    elevation_m: 67,
  },
  window: {
    start_at: "2026-05-12T20:00:00Z",
    duration_minutes: 10,
  },
  tle_age_limit: "24h",
};


describe("API client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the relative /api/v1 default and serializes search requests", async () => {
    const responseBody = { status: "no_result", results: [], diagnostics: {} };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(api.simpleSearch(request)).resolves.toEqual(responseBody);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/search/simple",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
  });

  it("preserves successful API response data", async () => {
    const responseBody = {
      status: "results",
      results: [{ rank: 1, match_score: 87.5 }],
      diagnostics: { returned_count: 1 },
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(responseBody), { status: 200 }),
    );

    await expect(api.simpleSearch(request)).resolves.toEqual(responseBody);
  });

  it("maps API error envelopes into ApiError", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message: "Invalid request.",
            details: {},
            field_errors: [{ field: "window.duration_minutes", message: "Too long." }],
          },
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(api.simpleSearch(request)).rejects.toMatchObject<ApiError>({
      name: "ApiError",
      status: 422,
      body: { code: "validation_error", message: "Invalid request." },
    });
  });
});

