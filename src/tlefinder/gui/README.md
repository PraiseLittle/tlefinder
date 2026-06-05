# TLE Finder — Web GUI

React + TypeScript + Vite client for the TLE Finder API. Implements every
requirement in [`docs/GUIREQUIREMENT.md`](../docs/GUIREQUIREMENT.md):
station persistence (GET / PUT `/api/v1/stations`), simple and advanced
satellite search (POST `/api/v1/search/{simple,advanced}`), full GUI-side
validation matching `schemas.py`, and explicit UTC/local time handling.

The GUI is an **API client only** — it never touches the YAML station store
or the core search modules directly (GUI-FR-06, GUI-FR-07, GUI-FR-08,
GUI-FR-14, GUI-FR-61).

## Prerequisites

- Node.js **≥ 20.10** (Vite 5 requirement)
- npm (or pnpm/yarn — any modern package manager works)
- A running TLE Finder API on `http://127.0.0.1:2626` for local development

## Quick start

```bash
cd gui
npm install
npm run dev          # starts Vite at http://localhost:2627
```

The dev server proxies `/api/*` requests to `http://127.0.0.1:2626` (see
[`vite.config.ts`](./vite.config.ts)), so the GUI talks to the real FastAPI
app while you're hacking. Adjust the proxy target if your API runs
elsewhere, or override at runtime with an env var:

```bash
# .env.local
VITE_API_BASE_URL=http://192.168.1.42:2626/api/v1
```

## Production build

```bash
npm run build        # outputs static assets to gui/dist/
npm run preview      # serves dist/ locally for a smoke test
```

## Serving the built GUI from FastAPI

The simplest deployment is to let FastAPI serve the static bundle alongside
the API. Add this to `src/tlefinder/api/app.py` after the routers are
registered:

```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles

GUI_DIST = Path(__file__).resolve().parents[3] / "gui" / "dist"
if GUI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=GUI_DIST, html=True), name="gui")
```

Run `npm run build` once, then start the API:

```bash
uvicorn tlefinder.api.app:app --reload
```

Open <http://127.0.0.1:2626/> — the GUI loads from `dist/`, and its
`fetch("/api/v1/...")` calls hit the API on the same origin (no CORS
config needed).

For a Docker image, copy `gui/dist/` into the API container at the same
relative path; FastAPI will pick it up automatically.

## Folder structure

```
gui/
├── index.html                  Vite entry HTML
├── package.json
├── tsconfig.json               + tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx                ReactDOM root
    ├── App.tsx                 App-level state, submission, modals, toasts
    ├── styles.css              Design system (tokens + components)
    ├── vite-env.d.ts
    ├── api/
    │   ├── client.ts           Typed fetch client + ApiError
    │   └── types.ts            TypeScript mirror of schemas.py
    ├── lib/
    │   ├── form.ts             Form-state shape + initial factory
    │   ├── format.ts           Display helpers (lat/lon/time/duration)
    │   └── validation.ts       GUI-side validation (matches API rules)
    └── components/
        ├── Header.tsx
        ├── StationSidebar.tsx       station list (left rail)
        ├── StationModal.tsx         add/edit station dialog
        ├── SearchPanel.tsx          simple/advanced composer
        ├── ResultsPanel.tsx         results column shell + states
        ├── ResultCard.tsx           one ranked candidate
        ├── SkyChart.tsx             polar az/alt plot of a pass
        ├── TimeBlock.tsx            label + date + time + copy
        ├── TleBlock.tsx             dark TLE viewer + copy
        ├── ToastStack.tsx           transient notifications
        └── icons.tsx                inline SVG icon set
```

## Design system

The visual language matches the rest of the TLE Finder docs: warm off-white
background, near-black text, a single brand-orange accent for primary
actions and selection. Type pairing is **Inter** (UI) + **JetBrains Mono**
(numeric / TLE data), loaded from Google Fonts in `index.html`.

All tokens live as CSS custom properties at the top of `src/styles.css`,
so theming is a matter of overriding `--accent`, `--bg`, `--text`, etc. on
`:root`.

## Type safety with `schemas.py`

`src/api/types.ts` is a manual port of the Pydantic models in
`src/tlefinder/api/schemas.py`. If the API contract changes, update both
files together — there is no codegen step. The (small) surface area makes
this trivial to keep in sync, and avoids dragging an OpenAPI generator
into the toolchain.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev`       | Vite dev server with HMR on :2627 |
| `npm run build`     | Type-check + production bundle to `dist/` |
| `npm run preview`   | Serve the production bundle locally |
| `npm run typecheck` | `tsc -b --noEmit` (CI-friendly) |

## License

Same license as the parent repository.
