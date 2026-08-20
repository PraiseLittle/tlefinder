import { useEffect } from "react";
import helpContent from "../../content/how-it-works.json";
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
      <div
        className="modal help-modal"
        role="dialog"
        aria-modal="true"
        aria-label={helpContent.dialogTitle}
      >
        <div className="modal-head">
          <h3>{helpContent.dialogTitle}</h3>
          <button className="icon-btn" onClick={onClose}><I.Close /></button>
        </div>
        <div className="modal-body help-body">
          <p className="help-lede">{helpContent.introduction}</p>

          <ol className="help-steps">
            {helpContent.steps.map((step) => (
              <li key={step.title}>
                <b>{step.title}</b> {step.body}
              </li>
            ))}
          </ol>

          {helpContent.sections.map((section) => (
            <section key={section.title}>
              <h4 className="help-h">{section.title}</h4>
              <ul className="help-list">
                {section.items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </section>
          ))}
        </div>
        <div className="modal-foot">
          <button className="btn btn-primary" onClick={onClose}>
            {helpContent.closeLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
