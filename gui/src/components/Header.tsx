import { useState } from "react";
import { HelpModal } from "./HelpModal";
import { I } from "./icons";

export function Header({
  online,
  tleStatus,
}: {
  online: boolean;
  tleStatus: { fresh: boolean; lastSync: string };
}) {
  const [helpOpen, setHelpOpen] = useState(false);
  return (
    <header className="app-header">
      <div className="brand">
        <img className="brand-mark" src="/cailabs-c.png" alt="Cailabs" />
        <span className="brand-name">TLE Finder</span>
        <span className="brand-tag">Satellite Pass Search</span>
        <button className="help-btn" onClick={() => setHelpOpen(true)} title="How to use TLE Finder">
          <I.Help size={12} /> How it works
        </button>
        {helpOpen && <HelpModal onClose={() => setHelpOpen(false)} />}
      </div>
      <div className="header-status">
        <span className={"status-dot" + (tleStatus.fresh ? "" : " stale")}>
          TLE feed · {tleStatus.fresh ? "fresh" : "stale"}
        </span>
        <span className="mono" style={{ opacity: 0.6 }}>
          last sync {tleStatus.lastSync}
        </span>
        <span className={"status-dot" + (online ? "" : " stale")}>
          API {online ? "online" : "offline"}
        </span>
      </div>
    </header>
  );
}
