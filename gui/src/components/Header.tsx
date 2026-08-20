import { useState } from "react";
import helpContent from "../../content/how-it-works.json";
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
        <button
          className="help-btn"
          onClick={() => setHelpOpen(true)}
          title={helpContent.buttonTitle}
        >
          <I.Help size={12} /> {helpContent.buttonLabel}
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
