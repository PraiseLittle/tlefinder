import { useState } from "react";
import type { TleResponse } from "@/api/types";
import { I } from "./icons";

export function TleBlock({ tle }: { tle: TleResponse }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard?.writeText(`${tle.name}\n${tle.line1}\n${tle.line2}`);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }
  return (
    <div className="tle-block">
      <button className="copy-btn" onClick={copy}>
        {copied ? (<><I.Check size={10} /> Copied</>) : (<><I.Copy /> Copy</>)}
      </button>
      <div className="tle-name">{tle.name}</div>
      <div className="tle-line">{tle.line1}</div>
      <div className="tle-line">{tle.line2}</div>
      <div
        style={{
          marginTop: 8,
          color: "rgba(245,242,236,0.5)",
          fontSize: 10.5,
          letterSpacing: 0.04,
        }}
      >
        epoch {tle.epoch_utc} · group{" "}
        <span style={{ color: "var(--accent)" }}>{tle.source_group}</span>
      </div>
    </div>
  );
}
