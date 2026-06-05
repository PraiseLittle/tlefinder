import { useState } from "react";
import type { SearchResultResponse } from "@/api/types";
import {
  durationStr,
  fmtAz,
  fmtTimeOffset,
  fmtTimeUTC,
  parseOffset,
} from "@/lib/format";
import { SkyChart } from "./SkyChart";
import { TimeBlock } from "./TimeBlock";
import { TleBlock } from "./TleBlock";
import { I } from "./icons";

interface Props {
  r: SearchResultResponse;
  displayTz: string; // "utc" or "+HH:MM"
}

export function ResultCard({ r, displayTz }: Props) {
  const [open, setOpen] = useState(r.rank === 1);
  const fmt = (iso: string) =>
    displayTz === "utc" ? fmtTimeUTC(iso) : fmtTimeOffset(iso, parseOffset(displayTz));

  return (
    <article className={"result-card" + (open ? " expanded" : "")}>
      <div className="result-row" onClick={() => setOpen((o) => !o)}>
        <div className="rank-badge">#{r.rank}</div>
        <div className="result-summary">
          <div className="sat-name">
            {r.satellite.name}
            <span className="group-pill mono">{r.satellite.tle.source_group}</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-faint)", fontWeight: 400 }}>
              NORAD {r.satellite.catalog_number}
            </span>
          </div>
          <div className="sat-meta">
            <span><span className="muted">start</span> <b className="mono" style={{ color: "var(--text)" }}>{fmt(r.geometry.start_time_utc)}</b></span>
            <span className="arrow">→</span>
            <span><span className="muted">end</span> <b className="mono" style={{ color: "var(--text)" }}>{fmt(r.geometry.end_time_utc)}</b></span>
            <span className="dot">·</span>
            <span><span className="muted">dur</span> <b className="mono" style={{ color: "var(--text)" }}>{durationStr(r.geometry.start_time_utc, r.geometry.end_time_utc)}</b></span>
          </div>
          <div className="sat-meta">
            <span><span className="muted">culm alt</span> <b className="mono" style={{ color: "var(--text)" }}>{r.geometry.culmination_altitude_deg.toFixed(1)}°</b></span>
            <span className="dot">·</span>
            <span><span className="muted">culm az</span> <b className="mono" style={{ color: "var(--text)" }}>{fmtAz(r.geometry.culmination_azimuth_deg)}</b></span>
            <span className="dot">·</span>
            <span><span className="muted">sat alt</span> <b className="mono" style={{ color: "var(--text)" }}>{r.metrics.satellite_altitude_km.toFixed(0)} km</b></span>
            {r.metrics.sun_proximity_deg != null && (
              <>
                <span className="dot">·</span>
                <span><span className="muted">sun</span> <b className="mono" style={{ color: "var(--text)" }}>{r.metrics.sun_proximity_deg.toFixed(0)}°</b></span>
              </>
            )}
          </div>
        </div>
        <div className="score-meter">
          <span className="score-val">{r.match_score.toFixed(1)}</span>
          <div className="bar"><div className="fill" style={{ width: r.match_score + "%" }} /></div>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--text-faint)", letterSpacing: "0.06em" }}>
            MATCH SCORE
          </span>
        </div>
        <div className="row-chev">
          <span className={"chev" + (open ? " open" : "")}><I.Chevron /></span>
        </div>
      </div>

      {open && (
        <div className="result-detail">
          <div className="detail-chart">
            <SkyChart geom={r.geometry} />
          </div>
          <div className="detail-stats-grid">
            <div className="detail-col">
              <h5>Pass geometry</h5>
              <TimeBlock label="Start" iso={r.geometry.start_time_utc} fmt={fmt} />
              <TimeBlock label="Culmination" iso={r.geometry.culmination_time_utc} fmt={fmt} accent />
              <TimeBlock label="End" iso={r.geometry.end_time_utc} fmt={fmt} />
              <div className="detail-kv"><span className="k">Duration</span><span className="v">{durationStr(r.geometry.start_time_utc, r.geometry.end_time_utc)}</span></div>
              <div className="detail-kv"><span className="k">Start azimuth</span><span className="v">{fmtAz(r.geometry.start_azimuth_deg)}</span></div>
              <div className="detail-kv"><span className="k">Culm. azimuth</span><span className="v">{fmtAz(r.geometry.culmination_azimuth_deg)}</span></div>
              <div className="detail-kv"><span className="k">End azimuth</span><span className="v">{fmtAz(r.geometry.end_azimuth_deg)}</span></div>
              <div className="detail-kv"><span className="k">Culm. altitude</span><span className="v">{r.geometry.culmination_altitude_deg.toFixed(2)}°</span></div>
            </div>
            <div className="detail-col">
              <h5>Metrics & ranking</h5>
              <div className="detail-kv"><span className="k">Match score</span><span className="v">{r.match_score.toFixed(2)} / 100</span></div>
              <div className="detail-kv"><span className="k">Satellite altitude</span><span className="v">{r.metrics.satellite_altitude_km.toFixed(1)} km</span></div>
              {r.metrics.sun_proximity_deg != null && (
                <div className="detail-kv"><span className="k">Sun proximity</span><span className="v">{r.metrics.sun_proximity_deg.toFixed(1)}°</span></div>
              )}
              <h5 style={{ marginTop: 14 }}>Satellite</h5>
              <div className="detail-kv"><span className="k">Name</span><span className="v">{r.satellite.name}</span></div>
              <div className="detail-kv"><span className="k">NORAD ID</span><span className="v">{r.satellite.catalog_number}</span></div>
              <div className="detail-kv"><span className="k">Source group</span><span className="v"><span className="group-pill mono">{r.satellite.tle.source_group}</span></span></div>
              <TimeBlock label="TLE epoch" iso={r.satellite.tle.epoch_utc} fmt={fmtTimeUTC} noCopy />
            </div>
          </div>
          <div className="detail-tle">
            <h5 style={{ margin: "0 0 6px" }}>Two-Line Element set</h5>
            <TleBlock tle={r.satellite.tle} />
          </div>
        </div>
      )}
    </article>
  );
}
