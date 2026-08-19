import type { PassGeometryResponse } from "@/api/types";

/**
 * Polar (az, alt) plot of a satellite pass — north is up, zenith is at the
 * centre. Three markers: pass start (ring), culmination (filled), pass end
 * (ring); accent-colored trajectory in between.
 */
export function SkyChart({ geom }: { geom: PassGeometryResponse }) {
  const R = 88;
  const cx = 100;
  const cy = 100;
  const project = (az: number, alt: number): [number, number] => {
    const r = R * (1 - Math.max(0, Math.min(90, alt)) / 90);
    const theta = ((az - 90) * Math.PI) / 180; // 0° = North up
    return [cx + r * Math.cos(theta), cy + r * Math.sin(theta)];
  };

  const samples = 32;
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  const fixAz = (a: number, b: number) => {
    if (b - a > 180) return b - 360;
    if (a - b > 180) return b + 360;
    return b;
  };

  const azC = fixAz(geom.start_azimuth_deg, geom.culmination_azimuth_deg);
  const azE = fixAz(azC, geom.end_azimuth_deg);
  const altS = 0;
  const altC = geom.culmination_altitude_deg;
  const altE = 0;

  const pts: [number, number][] = [];
  for (let i = 0; i <= samples; i++) {
    const t = i / samples;
    let az: number;
    let alt: number;
    if (t < 0.5) {
      const u = t / 0.5;
      az = lerp(geom.start_azimuth_deg, azC, u);
      alt = lerp(altS, altC, u);
    } else {
      const u = (t - 0.5) / 0.5;
      az = lerp(azC, azE, u);
      alt = lerp(altC, altE, u);
    }
    pts.push(project(az, alt));
  }
  const path = pts
    .map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1))
    .join(" ");
  const [sx, sy] = project(geom.start_azimuth_deg, 0);
  const [cxp, cyp] = project(azC, altC);
  const [ex, ey] = project(azE, 0);

  return (
    <div className="sky-chart">
      <svg viewBox="0 0 200 200">
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--border)" strokeWidth={1} />
        <circle cx={cx} cy={cy} r={(R * 2) / 3} fill="none" stroke="var(--border)" strokeDasharray="2 3" />
        <circle cx={cx} cy={cy} r={R / 3} fill="none" stroke="var(--border)" strokeDasharray="2 3" />
        <line x1={cx} y1={cy - R} x2={cx} y2={cy + R} stroke="var(--border)" strokeDasharray="2 3" />
        <line x1={cx - R} y1={cy} x2={cx + R} y2={cy} stroke="var(--border)" strokeDasharray="2 3" />
        <g fontFamily="var(--font-mono)" fontSize="8" fill="var(--text-faint)" textAnchor="middle">
          <text x={cx} y={cy - R - 3}>N</text>
          <text x={cx + R + 6} y={cy + 3}>E</text>
          <text x={cx} y={cy + R + 9}>S</text>
          <text x={cx - R - 6} y={cy + 3}>W</text>
          <text x={cx + 3} y={cy - 3} fill="var(--text-faint)">90°</text>
          <text x={cx + (R * 2) / 3 + 3} y={cy - 3}>30°</text>
        </g>
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinecap="round" />
        <circle cx={sx} cy={sy} r={3} fill="var(--surface)" stroke="var(--accent)" strokeWidth={1.6} />
        <circle cx={cxp} cy={cyp} r={4} fill="var(--accent)" />
        <circle cx={ex} cy={ey} r={3} fill="var(--surface)" stroke="var(--accent)" strokeWidth={1.6} />
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontFamily: "var(--font-mono)",
          fontSize: 9.5,
          color: "var(--text-faint)",
          padding: "2px 4px",
        }}
      >
        <span>start</span>
        <span>culmination</span>
        <span>end</span>
      </div>
    </div>
  );
}
