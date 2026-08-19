import { useEffect } from "react";
import { I } from "./icons";

/** How-to-use panel, opened from the header. */
export function HelpModal({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal help-modal" role="dialog" aria-modal="true" aria-label="How to use TLE Finder">
        <div className="modal-head">
          <h3>How to use TLE Finder</h3>
          <button className="icon-btn" onClick={onClose}><I.Close /></button>
        </div>
        <div className="modal-body help-body">
          <p className="help-lede">
            TLE Finder ranks satellite passes visible from one of your ground stations
            inside a time window, using the freshest TLE available.
          </p>

          <ol className="help-steps">
            <li>
              <b>Pick a station.</b> Select it in the left list, or add one with its
              latitude, longitude and elevation. The selected station defines the
              horizon, and the sun position drawn on each result.
            </li>
            <li>
              <b>Set the time window.</b> Enter a start time in UTC, or switch to local
              time and choose the offset. <b>Now + 5 min</b> fills in a start five
              minutes from now. Duration is capped at 30 minutes.
            </li>
            <li>
              <b>Choose the TLE age limit.</b> <span className="mono">24H</span> only
              accepts elements whose epoch is under a day old — tighter pointing,
              fewer candidates. <span className="mono">1W</span> widens the search.
            </li>
            <li>
              <b>Add criteria if needed.</b> Simple mode searches the whole selected
              group. Advanced adds minimum elevation, satellite altitude, orbit class
              and name filters — each section is optional until you enable it.
            </li>
            <li>
              <b>Run the search</b> and open a result card to see its geometry, metrics
              and the TLE used.
            </li>
          </ol>

          <h4 className="help-h">Reading the sky chart</h4>
          <ul className="help-list">
            <li>North is up, the outer circle is the horizon, the centre is the zenith.</li>
            <li>The orange arc is the pass, from rise through culmination to set; the filled dot marks the culmination.</li>
            <li>The yellow dot is the sun, with 10° and 20° halos. Passes crossing a halo risk stray light — the 10° ring is the hard exclusion.</li>
          </ul>

          <h4 className="help-h">Times and copying</h4>
          <ul className="help-list">
            <li>Results display in the timezone chosen in the search panel; the TLE epoch is always UTC.</li>
            <li>Copy buttons emit ISO 8601 with a <span className="mono">T</span> between date and time, ready to paste into a scheduler.</li>
          </ul>
        </div>
        <div className="modal-foot">
          <button className="btn btn-primary" onClick={onClose}>Got it</button>
        </div>
      </div>
    </div>
  );
}
