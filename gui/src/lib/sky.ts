/**
 * Sky geometry helpers for the polar pass chart.
 *  - passArc:  ONE smooth arc from pass start through culmination to pass end
 *              (spherical quadratic Bézier — passes exactly through all three).
 *  - sunPosition: apparent solar alt/az for a station at an instant (NOAA
 *              low-precision algorithm, ~0.01° — enough for a sky plot).
 *  - haloRing: the locus of points at a fixed angular radius from a sky point.
 */

const RAD = Math.PI / 180;

export interface SkyPoint {
  /** Degrees, 0 = North, increasing East. */
  az: number;
  /** Degrees above the horizon. */
  alt: number;
}

type Vec3 = [number, number, number];

function toVec(p: SkyPoint): Vec3 {
  const ca = Math.cos(p.alt * RAD);
  return [ca * Math.sin(p.az * RAD), ca * Math.cos(p.az * RAD), Math.sin(p.alt * RAD)];
}

function toSky(v: Vec3): SkyPoint {
  const n = Math.hypot(v[0], v[1], v[2]) || 1;
  const e = v[0] / n, no = v[1] / n, z = v[2] / n;
  return {
    az: ((Math.atan2(e, no) / RAD) + 360) % 360,
    alt: Math.asin(Math.max(-1, Math.min(1, z))) / RAD,
  };
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function unit(a: Vec3): Vec3 {
  const n = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / n, a[1] / n, a[2] / n];
}

export interface ArcGeometry {
  start_azimuth_deg: number;
  end_azimuth_deg: number;
  culmination_azimuth_deg: number;
  culmination_altitude_deg: number;
}

/** Single continuous arc: horizon → culmination → horizon, no kink. */
export function passArc(g: ArcGeometry, samples = 72): SkyPoint[] {
  const p0 = toVec({ az: g.start_azimuth_deg, alt: 0 });
  const p2 = toVec({ az: g.end_azimuth_deg, alt: 0 });
  const c = toVec({ az: g.culmination_azimuth_deg, alt: g.culmination_altitude_deg });
  // Control point chosen so the curve interpolates the culmination at t = 0.5.
  const p1: Vec3 = [0, 1, 2].map((i) => 2 * c[i] - (p0[i] + p2[i]) / 2) as Vec3;
  const out: SkyPoint[] = [];
  for (let i = 0; i <= samples; i++) {
    const t = i / samples;
    const a = (1 - t) * (1 - t), b = 2 * t * (1 - t), d = t * t;
    out.push(toSky([0, 1, 2].map((j) => a * p0[j] + b * p1[j] + d * p2[j]) as Vec3));
  }
  return out;
}

/** Apparent solar position seen from the station at `iso`. */
export function sunPosition(latitude: number, longitude: number, iso: string): SkyPoint {
  const jd = new Date(iso).getTime() / 86_400_000 + 2_440_587.5;
  const n = jd - 2_451_545.0;
  const meanLon = (280.460 + 0.9856474 * n) % 360;
  const meanAnom = ((357.528 + 0.9856003 * n) % 360) * RAD;
  const lambda =
    (meanLon + 1.915 * Math.sin(meanAnom) + 0.020 * Math.sin(2 * meanAnom)) * RAD;
  const eps = (23.439 - 0.0000004 * n) * RAD;
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lambda), Math.cos(lambda));
  const dec = Math.asin(Math.sin(eps) * Math.sin(lambda));
  const gmstHours = (18.697374558 + 24.06570982441908 * n) % 24;
  const lst = ((gmstHours < 0 ? gmstHours + 24 : gmstHours) * 15 + longitude) * RAD;
  const H = lst - ra;
  const lat = latitude * RAD;
  const alt = Math.asin(
    Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(H),
  );
  const az = Math.atan2(
    -Math.cos(dec) * Math.sin(H),
    Math.sin(dec) * Math.cos(lat) - Math.cos(dec) * Math.sin(lat) * Math.cos(H),
  );
  return { az: ((az / RAD) + 360) % 360, alt: alt / RAD };
}

/** Points at `radiusDeg` angular distance from `centre` (great-circle halo). */
export function haloRing(centre: SkyPoint, radiusDeg = 10, samples = 72): SkyPoint[] {
  const s = toVec(centre);
  const ref: Vec3 = Math.abs(s[2]) < 0.9 ? [0, 0, 1] : [0, 1, 0];
  const u = unit(cross(s, ref));
  const v = unit(cross(s, u));
  const cr = Math.cos(radiusDeg * RAD);
  const sr = Math.sin(radiusDeg * RAD);
  const out: SkyPoint[] = [];
  for (let i = 0; i <= samples; i++) {
    const th = (i / samples) * 2 * Math.PI;
    const c = Math.cos(th), sn = Math.sin(th);
    out.push(toSky([0, 1, 2].map(
      (j) => s[j] * cr + (u[j] * c + v[j] * sn) * sr,
    ) as Vec3));
  }
  return out;
}
