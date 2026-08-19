import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { App } from "@/App";


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
