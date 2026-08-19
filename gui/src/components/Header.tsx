export function Header({
  online,
  tleStatus,
}: {
  online: boolean;
  tleStatus: { fresh: boolean; lastSync: string };
}) {
  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true" />
        <span className="brand-name">TLE Finder</span>
        <span className="brand-tag">Optical Pass Search · v0.2</span>
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
