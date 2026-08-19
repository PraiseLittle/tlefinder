import type { ReactNode } from "react";
import type { SearchResponse } from "@/api/types";
import type { ApiError } from "@/api/client";
import { ResultCard } from "./ResultCard";
import { I } from "./icons";

export type SearchState = "idle" | "loading" | "ready" | "error";

interface Props {
  state: SearchState;
  response: SearchResponse | null;
  error: ApiError | null;
  displayTz: string;
}

export function ResultsPanel({ state, response, error, displayTz }: Props) {
  const tzLabel = displayTz === "utc" ? "UTC" : `UTC${displayTz}`;

  let body: ReactNode;
  if (state === "idle") {
    body = (
      <div className="state-block">
        <div className="glyph"><I.Sat /></div>
        <h3>No search run yet</h3>
        <p>
          Configure the search and press <b>Run search</b>. Results will appear
          here, ranked by match score.
        </p>
      </div>
    );
  } else if (state === "loading") {
    body = (
      <>
        <div className="progress-strip" />
        <div className="loading-block">
          <div className="state-block" style={{ padding: "0 0 4px" }}>
            <h3 style={{ margin: 0 }}>Searching…</h3>
            <p>POST /search dispatched to API. Awaiting ranked candidates.</p>
          </div>
          {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" />)}
        </div>
      </>
    );
  } else if (state === "error") {
    body = (
      <>
        <div className="api-error-banner">
          <strong>
            API error · <span className="mono">{error?.body.code || "internal_error"}</span>
          </strong>
          {error?.body.message || "The API rejected the request. Adjust inputs and retry."}
          {error?.body.field_errors && error.body.field_errors.length > 0 && (
            <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: 11.5 }}>
              {error.body.field_errors.map((fe, i) => (
                <li key={i}>
                  <span className="mono">{fe.field}</span> — {fe.message}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="state-block" style={{ padding: "30px 24px" }}>
          <div className="glyph"><I.Warn /></div>
          <h3>Could not complete search</h3>
          <p>The API returned an error. The request body is preserved — you can review your inputs and retry.</p>
        </div>
      </>
    );
  } else if (state === "ready" && response?.status === "no_result") {
    body = (
      <div className="state-block">
        <div className="glyph"><I.Empty /></div>
        <h3>No candidate satellite matched</h3>
        <p>
          No pass satisfied the search request. Try widening the time window,
          loosening filters, or lowering the score threshold.
        </p>
        {response.diagnostics && Object.keys(response.diagnostics).length > 0 && (
          <pre
            className="mono"
            style={{
              marginTop: 10,
              fontSize: 10.5,
              color: "var(--text-faint)",
              background: "transparent",
              maxWidth: 360,
              overflow: "auto",
              textAlign: "left",
            }}
          >
            {JSON.stringify(response.diagnostics, null, 2)}
          </pre>
        )}
      </div>
    );
  } else if (state === "ready" && response) {
    body = (
      <div className="results-body">
        {response.results.map((r) => (
          <ResultCard key={r.rank} r={r} displayTz={displayTz} />
        ))}
      </div>
    );
  }

  return (
    <section className="col-results">
      <div className="results-head">
        <div>
          <h2>
            Search results
            {state === "ready" && response?.status === "results" && (
              <span className="group-pill mono">
                {response.results.length} candidates
              </span>
            )}
          </h2>
          <div className="sub">
            {state === "idle" && "—"}
            {state === "loading" && "in progress · search dispatched"}
            {state === "ready" && response?.status === "results" &&
              "ranked by match score · API-provided order preserved"}
            {state === "ready" && response?.status === "no_result" && "no_result response received"}
            {state === "error" && "request failed · validation/API"}
          </div>
        </div>
        <span className="tz-pill">Times in {tzLabel}</span>
      </div>
      {body}
    </section>
  );
}
