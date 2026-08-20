import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { App } from "@/App";
import * as sky from "@/lib/sky";


const apiMock = vi.hoisted(() => ({
  listStations: vi.fn(),
  putStations: vi.fn(),
  simpleSearch: vi.fn(),
  advancedSearch: vi.fn(),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return { ...actual, api: apiMock };
});


beforeEach(() => {
  apiMock.listStations.mockResolvedValue({
    stations: [
      {
        name: "Paris Observatory",
        latitude: 48.8367,
        longitude: 2.3365,
        elevation_m: 67,
      },
    ],
  });
  apiMock.simpleSearch.mockResolvedValue({
    status: "no_result",
    results: [],
    diagnostics: { returned_count: 0 },
  });
});


it("loads stations through HTTP and completes the primary simple-search workflow", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Paris Observatory" }),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /run search/i }));

  await waitFor(() => expect(apiMock.simpleSearch).toHaveBeenCalledTimes(1));
  expect(apiMock.simpleSearch).toHaveBeenCalledWith(
    expect.objectContaining({
      station: expect.objectContaining({ name: "Paris Observatory" }),
      window: expect.objectContaining({ duration_minutes: 15 }),
    }),
  );
  expect(await screen.findByText("No candidate satellite matched")).toBeInTheDocument();
});


it("sets the UTC and explicit-offset local start times to five minutes from now", async () => {
  vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-05-17T21:55:30Z"));
  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Paris Observatory" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /now \+ 5 min/i }));
  expect(screen.getByDisplayValue("2026-05-17T22:00:30Z")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /local \+ offset/i }));
  await user.selectOptions(screen.getByLabelText("UTC offset"), "+02:00");
  await user.click(screen.getByRole("button", { name: /now \+ 5 min/i }));
  expect(document.querySelector<HTMLInputElement>('input[type="datetime-local"]')).toHaveValue(
    "2026-05-18T00:00:30.000",
  );
});


it("keeps result sky geometry tied to the station used for the search", async () => {
  apiMock.listStations.mockResolvedValue({
    stations: [
      { name: "Paris Observatory", latitude: 48.8367, longitude: 2.3365, elevation_m: 67 },
      { name: "Tokyo", latitude: 35.6762, longitude: 139.6503, elevation_m: 40 },
    ],
  });
  apiMock.simpleSearch.mockResolvedValue({
    status: "results",
    results: [{
      rank: 1,
      match_score: 91.5,
      satellite: {
        name: "ISS (ZARYA)",
        catalog_number: 25544,
        tle: {
          name: "ISS (ZARYA)",
          line1: "1 25544U 98067A   26139.50000000  .00000000  00000-0  00000-0 0  9999",
          line2: "2 25544  51.6400 100.0000 0005000  10.0000 350.0000 15.50000000123456",
          epoch_utc: "2026-05-19T12:00:00Z",
          source_group: "active",
        },
      },
      geometry: {
        start_time_utc: "2026-05-20T12:00:00Z",
        culmination_time_utc: "2026-05-20T12:05:00Z",
        end_time_utc: "2026-05-20T12:10:00Z",
        start_azimuth_deg: 95,
        culmination_azimuth_deg: 180,
        end_azimuth_deg: 265,
        culmination_altitude_deg: 55,
      },
      metrics: { satellite_altitude_km: 420, sun_proximity_deg: 35 },
      diagnostics: {},
    }],
    diagnostics: { returned_count: 1 },
  });
  const sunSpy = vi.spyOn(sky, "sunPosition");
  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("heading", { name: "Paris Observatory" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /run search/i }));
  expect((await screen.findAllByText("ISS (ZARYA)")).length).toBeGreaterThan(0);
  await waitFor(() => {
    expect(sunSpy).toHaveBeenLastCalledWith(48.8367, 2.3365, "2026-05-20T12:05:00Z");
  });

  await user.click(screen.getByRole("button", { name: /Tokyo/i }));
  expect(await screen.findByRole("heading", { name: "Tokyo" })).toBeInTheDocument();
  await waitFor(() => {
    expect(sunSpy).toHaveBeenLastCalledWith(48.8367, 2.3365, "2026-05-20T12:05:00Z");
  });
});
