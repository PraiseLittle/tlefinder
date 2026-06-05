import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { PersistedStation } from "@/api/types";
import { fmtElev, fmtLat, fmtLon } from "@/lib/format";
import type {
  AzimuthKey,
  RangeKey,
  SearchForm,
  SearchMode,
} from "@/lib/form";
import { I } from "./icons";

const OFFSETS = [
  "-12:00", "-11:00", "-10:00", "-09:00", "-08:00", "-07:00",
  "-06:00", "-05:00", "-04:00", "-03:00", "-02:00", "-01:00",
  "+00:00", "+01:00", "+02:00", "+03:00", "+04:00", "+05:00",
  "+05:30", "+06:00", "+07:00", "+08:00", "+09:00", "+09:30",
  "+10:00", "+11:00", "+12:00", "+13:00", "+14:00",
];

type SetForm = Dispatch<SetStateAction<SearchForm>>;

interface PanelProps {
  station: PersistedStation | null;
  mode: SearchMode;
  setMode: (m: SearchMode) => void;
  form: SearchForm;
  setForm: SetForm;
  errors: Record<string, string>;
  busy: boolean;
  onSubmit: () => void;
}

export function SearchPanel({
  station, mode, setMode, form, setForm, errors, busy, onSubmit,
}: PanelProps) {
  if (!station) {
    return (
      <div className="search-pane">
        <div className="state-block" style={{ padding: "80px 24px" }}>
          <div className="glyph"><I.Pin /></div>
          <h3>Select a ground station</h3>
          <p>Pick a station from the list, or add a new one, to compose a search.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="search-pane">
      <div className="station-card">
        <div className="icon-wrap"><I.Pin size={16} /></div>
        <div className="meta">
          <div className="meta-row">
            <h3>{station.name}</h3>
            <span className="meta-tag">Selected · OGS</span>
          </div>
          <div className="station-grid">
            <div>
              <label>Latitude</label>
              <div className="val">{fmtLat(station.latitude)}</div>
            </div>
            <div>
              <label>Longitude</label>
              <div className="val">{fmtLon(station.longitude)}</div>
            </div>
            <div>
              <label>Elevation</label>
              <div className="val">{fmtElev(station.elevation_m)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="mode-tabs" role="tablist">
        <button
          className={"mode-tab" + (mode === "simple" ? " active" : "")}
          onClick={() => setMode("simple")}
        >
          <I.Search size={12} /> Simple
        </button>
        <button
          className={"mode-tab" + (mode === "advanced" ? " active" : "")}
          onClick={() => setMode("advanced")}
        >
          <I.Sliders size={12} /> Advanced
        </button>
        <span style={{ flex: 1 }} />
      </div>

      <WindowFieldset form={form} setForm={setForm} errors={errors} />

      {mode === "advanced" && (
        <AdvancedSections form={form} setForm={setForm} errors={errors} />
      )}

      <div className="submit-bar">
        <button className="btn btn-primary" disabled={busy} onClick={onSubmit}>
          {busy ? "Searching…" : (<><I.Search /> Run search</>)}
        </button>
        {Object.keys(errors).length > 0 && (
          <span className="mono" style={{ fontSize: 11, color: "var(--danger)" }}>
            {Object.keys(errors).length} validation issue
            {Object.keys(errors).length > 1 ? "s" : ""}
          </span>
        )}
        <span className="submit-info">
          POST /search · {mode === "simple" ? "simple" : "advanced"}
          <br />
          group = {form.satellite_group}
        </span>
      </div>
    </div>
  );
}

// ── Window ────────────────────────────────────────────────────────
function WindowFieldset({
  form, setForm, errors,
}: { form: SearchForm; setForm: SetForm; errors: Record<string, string> }) {
  const setW = <K extends keyof SearchForm["window"]>(
    k: K, v: SearchForm["window"][K],
  ) => setForm((f) => ({ ...f, window: { ...f.window, [k]: v } }));

  return (
    <div className="adv-section" style={{ marginTop: 0 }}>
      <div className="adv-head open" style={{ cursor: "default" }}>
        <h4><I.Clock size={14} /> Search window <span className="enabled-pill">Required</span></h4>
        <div className="toggle-group" onClick={(e) => e.stopPropagation()}>
          <button className={form.window.tz_mode === "utc" ? "active" : ""} onClick={() => setW("tz_mode", "utc")}>UTC</button>
          <button className={form.window.tz_mode === "local" ? "active" : ""} onClick={() => setW("tz_mode", "local")}>Local + offset</button>
        </div>
      </div>
      <div className="adv-body">
        {form.window.tz_mode === "utc" ? (
          <div className="field-group">
            <label className="field-label">
              Start time (UTC) <span className="required">*</span>
              <span className="unit">ISO 8601 · ends in Z</span>
            </label>
            <input
              className={"text-input mono" + (errors["window.start_at"] ? " error" : "")}
              value={form.window.start_at_utc}
              onChange={(e) => setW("start_at_utc", e.target.value)}
              placeholder="2026-05-17T22:00:00Z"
            />
            {errors["window.start_at"] && <div className="field-error">{errors["window.start_at"]}</div>}
          </div>
        ) : (
          <div className="field-group">
            <label className="field-label">
              Local start time <span className="required">*</span>
              <span className="unit">ISO 8601 local + explicit offset</span>
            </label>
            <div className="datetime-with-offset">
              <input
                className={"text-input mono" + (errors["window.start_at"] ? " error" : "")}
                type="datetime-local"
                step={1}
                value={form.window.start_at_local}
                onChange={(e) => setW("start_at_local", e.target.value)}
              />
              <select
                className="text-input mono offset-select"
                value={form.window.utc_offset}
                onChange={(e) => setW("utc_offset", e.target.value)}
                aria-label="UTC offset"
              >
                {OFFSETS.map((o) => (
                  <option key={o} value={o}>UTC {o}</option>
                ))}
              </select>
            </div>
            {errors["window.start_at"] && <div className="field-error">{errors["window.start_at"]}</div>}
            <div className="field-help">The UTC offset is explicit and is not inferred from the station location.</div>
          </div>
        )}
        <div className="field-group">
          <label className="field-label">
            Duration <span className="required">*</span>
            <span className="unit">minutes · max 30</span>
          </label>
          <input
            className={"text-input mono" + (errors["window.duration_minutes"] ? " error" : "")}
            inputMode="decimal"
            value={form.window.duration_minutes}
            onChange={(e) => setW("duration_minutes", e.target.value)}
            placeholder="15"
            style={{ maxWidth: 180 }}
          />
          {errors["window.duration_minutes"] && (
            <div className="field-error">{errors["window.duration_minutes"]}</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Advanced sections ─────────────────────────────────────────────
function AdvancedSections({
  form, setForm, errors,
}: { form: SearchForm; setForm: SetForm; errors: Record<string, string> }) {
  return (
    <>
      <ResultControls form={form} setForm={setForm} errors={errors} />
      <RangeSection
        title="Apparent altitude at culmination"
        unit="° (0–90)"
        keyName="culmination_altitude_deg"
        bounds={[0, 90]}
        form={form} setForm={setForm} errors={errors}
      />
      <AzimuthSection form={form} setForm={setForm} errors={errors} />
      <RangeSection
        title="Sun proximity"
        unit="° (0–180)"
        keyName="sun_proximity_deg"
        bounds={[0, 180]}
        form={form} setForm={setForm} errors={errors}
      />
      <RangeSection
        title="Satellite altitude"
        unit="km (200–15000)"
        keyName="satellite_altitude_km"
        bounds={[200, 15000]}
        form={form} setForm={setForm} errors={errors}
      />
    </>
  );
}

function ResultControls({
  form, setForm, errors,
}: { form: SearchForm; setForm: SetForm; errors: Record<string, string> }) {
  const [open, setOpen] = useState(true);
  const set = <K extends keyof SearchForm["criteria"]>(
    k: K, v: SearchForm["criteria"][K],
  ) => setForm((f) => ({ ...f, criteria: { ...f.criteria, [k]: v } }));

  return (
    <div className="adv-section">
      <div className={"adv-head" + (open ? " open" : "")} onClick={() => setOpen((o) => !o)}>
        <h4><I.Sliders size={14} /> Selection & ranking <span className="enabled-pill">Required</span></h4>
        <span className="chev"><I.Chevron /></span>
      </div>
      {open && (
        <div className="adv-body">
          <div className="field-row">
            <div className="field-group" style={{ marginBottom: 0 }}>
              <label className="field-label">
                Result limit <span className="unit">positive integer</span>
              </label>
              <input
                className={"text-input mono" + (errors["criteria.result_limit"] ? " error" : "")}
                inputMode="numeric"
                value={form.criteria.result_limit}
                onChange={(e) => set("result_limit", e.target.value)}
                placeholder="10"
              />
              {errors["criteria.result_limit"] && (
                <div className="field-error">{errors["criteria.result_limit"]}</div>
              )}
            </div>
            <div className="field-group" style={{ marginBottom: 0 }}>
              <label className="field-label">
                Score threshold <span className="unit">0–100, optional</span>
              </label>
              <input
                className={"text-input mono" + (errors["criteria.score_threshold"] ? " error" : "")}
                inputMode="decimal"
                value={form.criteria.score_threshold}
                onChange={(e) => set("score_threshold", e.target.value)}
                placeholder="(no filter)"
              />
              {errors["criteria.score_threshold"] && (
                <div className="field-error">{errors["criteria.score_threshold"]}</div>
              )}
            </div>
          </div>
          <div className="field-group" style={{ marginTop: 14, marginBottom: 0 }}>
            <label className="field-label">Satellite group</label>
            <div className="toggle-group">
              {(["active", "visual", "amateur"] as const).map((g) => (
                <button
                  key={g}
                  className={form.satellite_group === g ? "active" : ""}
                  onClick={() => setForm((f) => ({ ...f, satellite_group: g }))}
                >
                  {g[0].toUpperCase() + g.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RangeSection({
  title, unit, keyName, bounds, form, setForm, errors,
}: {
  title: string;
  unit: string;
  keyName: RangeKey;
  bounds: [number, number];
  form: SearchForm;
  setForm: SetForm;
  errors: Record<string, string>;
}) {
  const enabled = form.criteria_enabled[keyName];
  const v = form.criteria[keyName];
  const [open, setOpen] = useState(false);

  function toggle() {
    setForm((f) => ({
      ...f,
      criteria_enabled: { ...f.criteria_enabled, [keyName]: !enabled },
    }));
  }
  function set(k: "minimum" | "maximum", val: string) {
    setForm((f) => ({
      ...f,
      criteria: { ...f.criteria, [keyName]: { ...v, [k]: val } },
    }));
  }

  return (
    <div className="adv-section">
      <div className={"adv-head" + (open || enabled ? " open" : "")} onClick={() => setOpen((o) => !o)}>
        <h4>
          {title}
          {enabled && <span className="enabled-pill">Enabled</span>}
        </h4>
        <div className="toggle-pill">
          <span className="mono" style={{ fontSize: 10, color: "var(--text-faint)" }}>{unit}</span>
          <span
            className={"switch" + (enabled ? " on" : "")}
            onClick={(e) => { e.stopPropagation(); toggle(); }}
          />
          <span className="chev"><I.Chevron /></span>
        </div>
      </div>
      {(open || enabled) && (
        <div className="adv-body">
          <div className="field-row">
            <div className="field-group" style={{ marginBottom: 0 }}>
              <label className="field-label">
                Minimum <span className="unit">{unit.split(" ")[0]}</span>
              </label>
              <input
                className={"text-input mono" + (errors[`criteria.${keyName}.min`] ? " error" : "")}
                disabled={!enabled}
                inputMode="decimal"
                value={v.minimum}
                onChange={(e) => set("minimum", e.target.value)}
                placeholder={String(bounds[0])}
              />
              {errors[`criteria.${keyName}.min`] && (
                <div className="field-error">{errors[`criteria.${keyName}.min`]}</div>
              )}
            </div>
            <div className="field-group" style={{ marginBottom: 0 }}>
              <label className="field-label">
                Maximum <span className="unit">{unit.split(" ")[0]}</span>
              </label>
              <input
                className={"text-input mono" + (errors[`criteria.${keyName}.max`] ? " error" : "")}
                disabled={!enabled}
                inputMode="decimal"
                value={v.maximum}
                onChange={(e) => set("maximum", e.target.value)}
                placeholder={String(bounds[1])}
              />
              {errors[`criteria.${keyName}.max`] && (
                <div className="field-error">{errors[`criteria.${keyName}.max`]}</div>
              )}
            </div>
          </div>
          {errors[`criteria.${keyName}.order`] && (
            <div className="field-error" style={{ marginTop: 8 }}>
              {errors[`criteria.${keyName}.order`]}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AzimuthSection({
  form, setForm, errors,
}: { form: SearchForm; setForm: SetForm; errors: Record<string, string> }) {
  const [open, setOpen] = useState(false);
  const keys: AzimuthKey[] = [
    "start_azimuth_deg",
    "culmination_azimuth_deg",
    "end_azimuth_deg",
  ];
  const anyEnabled = keys.some((k) => form.criteria_enabled[k]);

  return (
    <div className="adv-section">
      <div className={"adv-head" + (open || anyEnabled ? " open" : "")} onClick={() => setOpen((o) => !o)}>
        <h4>
          Azimuth targets
          {anyEnabled && <span className="enabled-pill">Enabled</span>}
        </h4>
        <div className="toggle-pill">
          <span className="mono" style={{ fontSize: 10, color: "var(--text-faint)" }}>° · target ± tolerance</span>
          <span className="chev"><I.Chevron /></span>
        </div>
      </div>
      {(open || anyEnabled) && (
        <div className="adv-body">
          {keys.map((k) => (
            <AzimuthRow key={k} keyName={k} form={form} setForm={setForm} errors={errors} />
          ))}
        </div>
      )}
    </div>
  );
}

function AzimuthRow({
  keyName, form, setForm, errors,
}: {
  keyName: AzimuthKey;
  form: SearchForm;
  setForm: SetForm;
  errors: Record<string, string>;
}) {
  const enabled = form.criteria_enabled[keyName];
  const v = form.criteria[keyName];
  const labels: Record<AzimuthKey, string> = {
    start_azimuth_deg: "Start azimuth",
    culmination_azimuth_deg: "Culmination azimuth",
    end_azimuth_deg: "End azimuth",
  };
  function toggle() {
    setForm((f) => ({
      ...f,
      criteria_enabled: { ...f.criteria_enabled, [keyName]: !enabled },
    }));
  }
  function set(k: "target" | "tolerance", val: string) {
    setForm((f) => ({
      ...f,
      criteria: { ...f.criteria, [keyName]: { ...v, [k]: val } },
    }));
  }
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "148px 1fr 1fr 32px",
        gap: 10,
        alignItems: "flex-end",
        marginBottom: 12,
      }}
    >
      <div style={{ paddingBottom: 8, fontSize: 12, color: "var(--text-muted)" }}>
        {labels[keyName]}
      </div>
      <div className="field-group" style={{ marginBottom: 0 }}>
        <label className="field-label">
          Target <span className="unit">° (0–360)</span>
        </label>
        <input
          className={"text-input mono" + (errors[`criteria.${keyName}.target`] ? " error" : "")}
          disabled={!enabled}
          inputMode="decimal"
          value={v.target}
          onChange={(e) => set("target", e.target.value)}
          placeholder="180"
        />
      </div>
      <div className="field-group" style={{ marginBottom: 0 }}>
        <label className="field-label">
          ± Tolerance <span className="unit">° (0–180)</span>
        </label>
        <input
          className={"text-input mono" + (errors[`criteria.${keyName}.tol`] ? " error" : "")}
          disabled={!enabled}
          inputMode="decimal"
          value={v.tolerance}
          onChange={(e) => set("tolerance", e.target.value)}
          placeholder="20"
        />
      </div>
      <span
        className={"switch" + (enabled ? " on" : "")}
        onClick={toggle}
        style={{ marginBottom: 10 }}
      />
    </div>
  );
}
