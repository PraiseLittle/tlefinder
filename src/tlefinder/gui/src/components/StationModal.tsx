import { useState } from "react";
import type { PersistedStation } from "@/api/types";
import { validateStation } from "@/lib/validation";
import { I } from "./icons";

interface Props {
  initial: (PersistedStation & { id?: string }) | null;
  takenNames: string[];
  onClose: () => void;
  onSave: (payload: PersistedStation & { id?: string }) => void;
}

export function StationModal({ initial, takenNames, onClose, onSave }: Props) {
  const isNew = !initial?.name;
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    latitude: (initial?.latitude ?? "") as number | string,
    longitude: (initial?.longitude ?? "") as number | string,
    elevation_m: (initial?.elevation_m ?? "") as number | string,
  });
  const [errs, setErrs] = useState<Record<string, string>>({});

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function submit() {
    const { errors, payload } = validateStation(
      form,
      takenNames,
      initial?.name,
    );
    if (Object.keys(errors).length) {
      setErrs(errors);
      return;
    }
    if (payload) onSave({ ...payload, id: initial?.id });
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true">
        <div className="modal-head">
          <h3>{isNew ? "Add optical ground station" : "Edit station"}</h3>
          <button className="icon-btn" onClick={onClose}>
            <I.Close />
          </button>
        </div>
        <div className="modal-body">
          <div className="field-group">
            <label className="field-label">
              Name <span className="required">*</span>
            </label>
            <input
              className={"text-input" + (errs.name ? " error" : "")}
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="e.g. Paris–Saclay OGS"
              autoFocus
            />
            {errs.name && <div className="field-error">{errs.name}</div>}
          </div>
          <div className="field-row">
            <div className="field-group">
              <label className="field-label">
                Latitude <span className="required">*</span>
                <span className="unit">° decimal</span>
              </label>
              <input
                className={"text-input mono" + (errs.latitude ? " error" : "")}
                value={form.latitude}
                onChange={(e) => set("latitude", e.target.value)}
                placeholder="48.7100"
                inputMode="decimal"
              />
              {errs.latitude && <div className="field-error">{errs.latitude}</div>}
            </div>
            <div className="field-group">
              <label className="field-label">
                Longitude <span className="required">*</span>
                <span className="unit">° decimal</span>
              </label>
              <input
                className={"text-input mono" + (errs.longitude ? " error" : "")}
                value={form.longitude}
                onChange={(e) => set("longitude", e.target.value)}
                placeholder="2.1700"
                inputMode="decimal"
              />
              {errs.longitude && (
                <div className="field-error">{errs.longitude}</div>
              )}
            </div>
          </div>
          <div className="field-group">
            <label className="field-label">
              Elevation above MSL <span className="required">*</span>
              <span className="unit">m</span>
            </label>
            <input
              className={"text-input mono" + (errs.elevation_m ? " error" : "")}
              value={form.elevation_m}
              onChange={(e) => set("elevation_m", e.target.value)}
              placeholder="156"
              inputMode="decimal"
            />
            {errs.elevation_m && (
              <div className="field-error">{errs.elevation_m}</div>
            )}
            <div className="field-help">Range −500 m to 8000 m.</div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={submit}>
            <I.Check /> {isNew ? "Add station" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
