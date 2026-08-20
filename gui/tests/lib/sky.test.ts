import { describe, expect, it } from "vitest";

import { haloRing, passArc, sunPosition, type SkyPoint } from "@/lib/sky";


function angularDistance(a: SkyPoint, b: SkyPoint): number {
  const rad = Math.PI / 180;
  const cosDistance =
    Math.sin(a.alt * rad) * Math.sin(b.alt * rad) +
    Math.cos(a.alt * rad) * Math.cos(b.alt * rad) * Math.cos((a.az - b.az) * rad);
  return Math.acos(Math.max(-1, Math.min(1, cosDistance))) / rad;
}


describe("sky geometry", () => {
  it("builds one arc through the pass endpoints and culmination", () => {
    const arc = passArc({
      start_azimuth_deg: 350,
      end_azimuth_deg: 20,
      culmination_azimuth_deg: 5,
      culmination_altitude_deg: 62,
    });

    expect(arc).toHaveLength(73);
    expect(arc[0].az).toBeCloseTo(350, 8);
    expect(arc[0].alt).toBeCloseTo(0, 8);
    expect(arc[36].az).toBeCloseTo(5, 8);
    expect(arc[36].alt).toBeCloseTo(62, 8);
    expect(arc[72].az).toBeCloseTo(20, 8);
    expect(arc[72].alt).toBeCloseTo(0, 8);
  });

  it("keeps every halo sample at the requested angular radius", () => {
    const centre = { az: 120, alt: 45 };
    const ring = haloRing(centre, 10);

    expect(ring).toHaveLength(73);
    for (const point of ring) {
      expect(angularDistance(centre, point)).toBeCloseTo(10, 8);
    }
  });

  it("places the summer-solstice midday sun high in the southern Paris sky", () => {
    const sun = sunPosition(48.8367, 2.3365, "2026-06-21T12:00:00Z");

    expect(sun.alt).toBeGreaterThan(60);
    expect(sun.alt).toBeLessThan(70);
    expect(sun.az).toBeGreaterThan(170);
    expect(sun.az).toBeLessThan(210);
  });
});
