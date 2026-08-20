import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { TimeBlock } from "@/components/TimeBlock";


it("copies the displayed time as ISO 8601", async () => {
  const user = userEvent.setup();
  const writeText = vi.spyOn(navigator.clipboard, "writeText");
  render(
    <TimeBlock
      label="Start"
      iso="2026-05-17T22:00:00Z"
      fmt={() => "2026-05-18 00:00:00 +02:00"}
    />,
  );

  await user.click(screen.getByTitle("Copy ISO 8601 timestamp"));
  expect(writeText).toHaveBeenCalledWith("2026-05-18T00:00:00+02:00");
});
