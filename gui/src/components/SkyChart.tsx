import type { PassGeometryResponse, StationCoordinates } from "@/api/types";
import { haloRing, passArc, sunPosition, type SkyPoint } from "@/lib/sky";

const SUN_HALO_DEG = 10;
const SUN_HALO_WIDE_DEG = 20;

/**
 * Polar (az, alt) plot of a satellite pass — north is up, zenith is at the
 * centre. One continuous arc from pass start through culmination to pass end,
 * plus the sun with 10° and 20° halos when it is near the visible sky.
 */
export function SkyChart({
  geom,
  station,
}: {
  geom: PassGeometryResponse;
  station?: StationCoordinates | null;
}) {
  const R = 88;
  const cx = 100;
  const cy = 100;
  const project = (p: SkyPoint): [number, number] => {
    const r = R * (1 - Math.max(0, Math.min(90, p.alt)) / 90);
    const theta = ((p.az - 90) * Math.PI) / 180;
    return [cx + r * Math.cos(theta), cy + r * Math.sin(theta)];
  };
  const toPath = (pts: SkyPoint[], close = false) =>
    pts
      .map(project)
      .map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1))
      .join(" ") + (close ? " Z" : "");

  const arc = passArc(geom);
  const [sx, sy] = project({ az: geom.start_azimuth_deg, alt: 0 });
  const [ex, ey] = project({ az: geom.end_azimuth_deg, alt: 0 });
  const [ux, uy] = project({
    az: geom.culmination_azimuth_deg,
    alt: geom.culmination_altitude_deg,
  });

  const sun = station
    ? sunPosition(station.latitude, station.longitude, geom.culmination_time_utc)
    : null;
  const sunUp = sun != null && sun.alt >= 0;
  const sunNearHorizon = sun != null && sun.alt >= -SUN_HALO_DEG;
  const sunNearWide = sun != null && sun.alt >= -SUN_HALO_WIDE_DEG;
  const [sunX, sunY] = sun ? project(sun) : [0, 0];

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

        {sunNearWide && sun && (
          <path
            d={toPath(haloRing(sun, SUN_HALO_WIDE_DEG), true)}
            fill="var(--sun-fill-wide)"
            stroke="var(--sun)"
            strokeWidth={1}
            strokeDasharray="2 3"
          />
        )}
        {sunNearHorizon && sun && (
          <path
            d={toPath(haloRing(sun, SUN_HALO_DEG), true)}
            fill="var(--sun-fill)"
            stroke="var(--sun)"
            strokeWidth={1.2}
            strokeDasharray="3 2.5"
          />
        )}

        <path d={toPath(arc)} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinecap="round" />
        <circle cx={sx} cy={sy} r={3} fill="var(--surface)" stroke="var(--accent)" strokeWidth={1.6} />
        <circle cx={ex} cy={ey} r={3} fill="var(--surface)" stroke="var(--accent)" strokeWidth={1.6} />
        <circle cx={ux} cy={uy} r={4} fill="var(--accent)" />

        {sunUp && (
          <>
            <circle cx={sunX} cy={sunY} r={4} fill="var(--sun)" />
            <circle cx={sunX} cy={sunY} r={6.5} fill="none" stroke="var(--sun)" strokeWidth={0.8} opacity={0.5} />
          </>
        )}
      </svg>
      <div className="sky-legend">
        <span><i className="swatch arc" /> pass arc</span>
        <span><i className="swatch culm" /> culmination</span>
        <span>
          <i className="swatch sun" />{" "}
          {sun == null
            ? "sun n/a"
            : sunUp
              ? `sun · ${SUN_HALO_DEG}°/${SUN_HALO_WIDE_DEG}° halos`
              : `sun ${sun.alt.toFixed(0)}° (below horizon)`}
        </span>
      </div>
    </div>
  );
}
