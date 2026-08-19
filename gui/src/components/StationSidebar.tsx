import type { PersistedStation } from "@/api/types";
import { fmtElev, fmtLat, fmtLon } from "@/lib/format";
import { I } from "./icons";

export interface StationRow extends PersistedStation {
  id: string;
}

interface Props {
  stations: StationRow[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onEdit: (st: StationRow) => void;
  onDelete: (id: string) => void;
  onAdd: () => void;
}

export function StationSidebar({
  stations,
  selectedId,
  onSelect,
  onEdit,
  onDelete,
  onAdd,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="section-head">
        <h2>Ground Stations</h2>
        <span className="count mono">
          {String(stations.length).padStart(2, "0")}
        </span>
      </div>
      <div className="station-list">
        {stations.map((st) => (
          <button
            key={st.id}
            className={"station-item" + (st.id === selectedId ? " selected" : "")}
            onClick={() => onSelect(st.id)}
          >
            <div className="station-name">
              <span>{st.name}</span>
              <span className="station-actions">
                <span
                  className="icon-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(st);
                  }}
                  title="Edit"
                >
                  <I.Pencil />
                </span>
                <span
                  className="icon-btn danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(st.id);
                  }}
                  title="Delete"
                >
                  <I.Trash />
                </span>
              </span>
            </div>
            <div className="station-coords">
              {fmtLat(st.latitude)} · {fmtLon(st.longitude)} · {fmtElev(st.elevation_m)}
            </div>
          </button>
        ))}
        {stations.length === 0 && (
          <div className="state-block" style={{ padding: "40px 16px" }}>
            <div className="glyph">
              <I.Pin />
            </div>
            <h3>No stations yet</h3>
            <p>Add an optical ground station to start searching.</p>
          </div>
        )}
      </div>
      <div className="sidebar-foot">
        <button className="add-station-btn" onClick={onAdd}>
          <I.Plus /> Add station
        </button>
      </div>
    </aside>
  );
}
