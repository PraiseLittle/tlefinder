import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { Header } from "@/components/Header";


it("opens and closes the how-to dialog", async () => {
  const user = userEvent.setup();
  render(<Header online tleStatus={{ fresh: true, lastSync: "just now" }} />);

  await user.click(screen.getByRole("button", { name: /how it works/i }));
  expect(screen.getByRole("dialog", { name: /how to use tle finder/i })).toBeInTheDocument();

  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: /how to use tle finder/i })).not.toBeInTheDocument();
});
