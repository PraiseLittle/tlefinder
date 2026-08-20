/** Display + formatting helpers. */

export function fmtLat(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${Math.abs(v).toFixed(4)}° ${v >= 0 ? "N" : "S"}`;
}

export function fmtLon(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${Math.abs(v).toFixed(4)}° ${v >= 0 ? "E" : "W"}`;
}

export function fmtElev(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${v.toFixed(0)} m`;
}

export function fmtAz(deg: number): string {
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"];
  const idx = Math.round(((deg % 360) / 45));
  return `${deg.toFixed(1)}° ${dirs[idx]}`;
}

const pad = (n: number) => String(n).padStart(2, "0");

export function fmtTimeUTC(iso: string): string {
  const d = new Date(iso);
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`
  );
}

export function fmtTimeOffset(iso: string, offsetMin: number): string {
  const d = new Date(new Date(iso).getTime() + offsetMin * 60_000);
  const sign = offsetMin >= 0 ? "+" : "-";
  const oh = pad(Math.floor(Math.abs(offsetMin) / 60));
  const om = pad(Math.abs(offsetMin) % 60);
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} ` +
    `${sign}${oh}:${om}`
  );
}

/** Convert a displayed timestamp into a scheduler-ready ISO 8601 value. */
export function isoCopyText(formatted: string): string {
  return formatted.replace(" ", "T").replace(/\s+([+-]\d{2}:\d{2})$/, "$1");
}

export function durationStr(startIso: string, endIso: string): string {
  const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}m ${pad(r)}s`;
}

/** Parse an ISO offset like "+01:00" or "-05:00" into total minutes. */
export function parseOffset(offset: string): number {
  if (offset === "utc" || !offset) return 0;
  const m = /([+-])(\d{2}):(\d{2})/.exec(offset);
  if (!m) return 0;
  return (
    (m[1] === "+" ? 1 : -1) * (parseInt(m[2], 10) * 60 + parseInt(m[3], 10))
  );
}
