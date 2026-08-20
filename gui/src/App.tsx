import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api } from "@/api/client";
import type {
  AdvancedSearchRequest,
  PersistedStation,
  SearchResponse,
  SimpleSearchRequest,
  StationCoordinates,
} from "@/api/types";
import { Header } from "@/components/Header";
import { ResultsPanel, type SearchState } from "@/components/ResultsPanel";
import { SearchPanel } from "@/components/SearchPanel";
import { StationModal } from "@/components/StationModal";
import { StationSidebar, type StationRow } from "@/components/StationSidebar";
import { ToastStack, type Toast } from "@/components/ToastStack";
import { makeInitialForm, type SearchMode } from "@/lib/form";
import { buildSearchRequest } from "@/lib/validation";

function withId(p: PersistedStation, i: number): StationRow {
  return { ...p, id: `st_${i}_${p.name}` };
}

export function App() {
  const [stations, setStations] = useState<StationRow[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stationsLoading, setStationsLoading] = useState(true);
  const [stationsError, setStationsError] = useState<string | null>(null);
  const [online, setOnline] = useState(false);

  const [mode, setMode] = useState<SearchMode>("simple");
  const [form, setForm] = useState(makeInitialForm);

  const [reqState, setReqState] = useState<SearchState>("idle");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [resultStation, setResultStation] = useState<StationCoordinates | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);

  const [modal, setModal] = useState<{ station: StationRow | null } | null>(
    null,
  );
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastIdRef = useRef(0);

  // ── Toast helper ─────────────────────────────────────────────
  const pushToast = useCallback(
    (msg: string, kind: Toast["kind"] = "info") => {
      const id = ++toastIdRef.current;
      setToasts((ts) => [...ts, { id, msg, kind }]);
      window.setTimeout(
        () => setToasts((ts) => ts.filter((t) => t.id !== id)),
        3200,
      );
    },
    [],
  );

  // ── Initial station load ─────────────────────────────────────
  useEffect(() => {
    const ctrl = new AbortController();
    api.listStations(ctrl.signal)
      .then((res) => {
        const withIds = res.stations.map(withId);
        setStations(withIds);
        if (withIds.length > 0) setSelectedId(withIds[0].id);
        setStationsLoading(false);
        setOnline(true);
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted) return;
        const message =
          err instanceof ApiError ? err.body.message : "Failed to reach API.";
        setStationsError(message);
        setStationsLoading(false);
        setOnline(false);
        pushToast(`Could not load stations: ${message}`, "error");
      });
    return () => ctrl.abort();
  }, [pushToast]);

  const station =
    stations.find((s) => s.id === selectedId) ?? null;

  // ── Station CRUD ────────────────────────────────────────────
  const persistStations = useCallback(
    async (next: StationRow[], successMsg: string) => {
      try {
        const res = await api.putStations({
          stations: next.map(({ id, ...rest }) => rest),
        });
        const withIds = res.stations.map(withId);
        setStations(withIds);
        pushToast(successMsg, "success");
        return withIds;
      } catch (err) {
        const message =
          err instanceof ApiError ? err.body.message : "Failed to save stations.";
        pushToast(`Save failed: ${message}`, "error");
        throw err;
      }
    },
    [pushToast],
  );

  const saveStation = useCallback(
    async (payload: PersistedStation & { id?: string }) => {
      const { id, ...rest } = payload;
      let next: StationRow[];
      let msg: string;
      if (id) {
        next = stations.map((s) =>
          s.id === id ? { ...s, ...rest } : s,
        );
        msg = `Updated “${rest.name}”`;
      } else {
        next = [
          ...stations,
          { ...rest, id: `st_${Date.now()}` },
        ];
        msg = `Added “${rest.name}” via API`;
      }
      try {
        const persisted = await persistStations(next, msg);
        if (!id) {
          const created = persisted.find((s) => s.name === rest.name);
          if (created) setSelectedId(created.id);
        }
        setModal(null);
      } catch {
        // Keep the modal open so the user can correct and retry.
      }
    },
    [stations, persistStations],
  );

  const deleteStation = useCallback(
    async (id: string) => {
      const st = stations.find((s) => s.id === id);
      if (!st) return;
      if (!window.confirm(`Delete station "${st.name}"?`)) return;
      const next = stations.filter((s) => s.id !== id);
      try {
        await persistStations(next, `Deleted “${st.name}”`);
        if (selectedId === id) {
          setSelectedId(next[0]?.id ?? null);
        }
      } catch {
        /* persistStations already toasted */
      }
    },
    [stations, selectedId, persistStations],
  );

  // ── Submit ──────────────────────────────────────────────────
  const { errors, request } = useMemo(
    () => buildSearchRequest(mode, station, form),
    [mode, station, form],
  );

  const onSubmit = useCallback(async () => {
    if (!request) return;
    setReqState("loading");
    setApiError(null);
    setResponse(null);
    setResultStation(null);
    try {
      const resp =
        mode === "simple"
          ? await api.simpleSearch(request as SimpleSearchRequest)
          : await api.advancedSearch(request as AdvancedSearchRequest);
      setResponse(resp);
      setResultStation({ ...request.station });
      setReqState("ready");
      if (resp.status === "results") {
        pushToast(
          `${resp.results.length} candidate${resp.results.length > 1 ? "s" : ""} returned`,
          "success",
        );
      } else {
        pushToast("Search returned no_result", "info");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err);
      } else {
        setApiError(
          new ApiError(
            {
              code: "internal_error",
              message:
                err instanceof Error ? err.message : "Unknown error",
              details: {},
              field_errors: [],
            },
            0,
          ),
        );
      }
      setReqState("error");
      pushToast("Search failed — see panel", "error");
    }
  }, [request, mode, pushToast]);

  const displayTz =
    form.window.tz_mode === "local" ? form.window.utc_offset : "utc";

  return (
    <>
      <Header
        online={online}
        tleStatus={{ fresh: true, lastSync: "—" }}
      />
      <div className="app-main">
        <StationSidebar
          stations={stations}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onEdit={(st) => setModal({ station: st })}
          onDelete={deleteStation}
          onAdd={() => setModal({ station: null })}
        />

        <section className="col-search">
          {stationsLoading ? (
            <div className="state-block" style={{ padding: "80px 24px" }}>
              <h3>Loading stations…</h3>
              <p>Fetching persisted station list from the API.</p>
            </div>
          ) : stationsError ? (
            <div className="state-block" style={{ padding: "80px 24px" }}>
              <h3>Could not reach API</h3>
              <p>{stationsError}</p>
            </div>
          ) : (
            <SearchPanel
              station={station}
              mode={mode}
              setMode={setMode}
              form={form}
              setForm={setForm}
              errors={errors}
              busy={reqState === "loading"}
              onSubmit={onSubmit}
            />
          )}
        </section>

        <ResultsPanel
          state={reqState}
          response={response}
          error={apiError}
          station={resultStation}
          displayTz={displayTz}
        />
      </div>

      {modal && (
        <StationModal
          initial={modal.station}
          takenNames={stations.map((s) => s.name)}
          onClose={() => setModal(null)}
          onSave={saveStation}
        />
      )}

      <ToastStack toasts={toasts} />
    </>
  );
}
