import { useState } from "react";
import type { MouseEvent } from "react";
import { I } from "./icons";

interface TimeBlockProps {
  label: string;
  iso: string;
  fmt: (iso: string) => string;
  accent?: boolean;
  noCopy?: boolean;
}

export function TimeBlock({
  label, iso, fmt, accent = false, noCopy = false,
}: TimeBlockProps) {
  const [copied, setCopied] = useState(false);
  const formatted = fmt(iso);
  const idx = formatted.indexOf(" ");
  const datePart = idx > 0 ? formatted.slice(0, idx) : formatted;
  const timePart = idx > 0 ? formatted.slice(idx + 1) : "";

  function copy(e: MouseEvent) {
    e.stopPropagation();
    navigator.clipboard?.writeText(formatted);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  const cls = ["time-block", accent ? "accent" : ""].filter(Boolean).join(" ");
  return (
    <div className={cls}>
      <div className="tlabel">{label}</div>
      <div className="tvalue">
        <span className="tdate">{datePart}</span>
        <span className="ttime">{timePart}</span>
      </div>
      {!noCopy && (
        <button
          className={"copy-time" + (copied ? " copied" : "")}
          onClick={copy}
          title="Copy timestamp"
        >
          {copied ? <I.Check size={12} /> : <I.Copy size={11} />}
        </button>
      )}
    </div>
  );
}
