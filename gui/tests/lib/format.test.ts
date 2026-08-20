import { describe, expect, it } from "vitest";

import { isoCopyText } from "@/lib/format";


describe("ISO clipboard formatting", () => {
  it("converts a displayed UTC timestamp", () => {
    expect(isoCopyText("2026-05-17 22:00:00Z")).toBe("2026-05-17T22:00:00Z");
  });

  it("converts a displayed timestamp with an explicit UTC offset", () => {
    expect(isoCopyText("2026-05-18 00:00:00 +02:00")).toBe(
      "2026-05-18T00:00:00+02:00",
    );
  });
});
