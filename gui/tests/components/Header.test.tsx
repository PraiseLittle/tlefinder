import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";

import { Header } from "@/components/Header";
import helpContent from "../../content/how-it-works.json";


it("opens and closes the how-to dialog", async () => {
  const user = userEvent.setup();
  render(<Header online tleStatus={{ fresh: true, lastSync: "just now" }} />);

  await user.click(screen.getByRole("button", { name: /how it works/i }));
  expect(screen.getByRole("dialog", { name: /how to use tle finder/i })).toBeInTheDocument();
  expect(screen.getByText(helpContent.introduction)).toBeInTheDocument();
  expect(screen.getByText(helpContent.steps[0].title)).toBeInTheDocument();
  expect(screen.getByText(helpContent.sections[0].title)).toBeInTheDocument();

  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog", { name: /how to use tle finder/i })).not.toBeInTheDocument();
});
