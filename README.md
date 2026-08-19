# TLE Finder Monorepo

TLE Finder is one Git repository containing three independently buildable projects:

- `core/` — the `tlefinder-core` Python distribution and benchmark command.
- `api/` — the `tlefinder-api` Python distribution and FastAPI application.
- `gui/` — the `tlefinder-gui` Vite/React frontend.

Dependency direction is one way: API depends on Core through the public `tlefinder.core` contract, and GUI communicates with API only over HTTP. Core never depends on API or GUI. The two Python distributions share the implicit PEP 420 `tlefinder` namespace, so the public imports remain `tlefinder.core` and `tlefinder.api` without either project owning `src/tlefinder/__init__.py`.

## Local development

Follow each component README for installation and tests. Until the container workflow arrives in Phase 23, run API and GUI in separate terminals:

```powershell
# Terminal 1
cd api
poetry install
poetry run uvicorn tlefinder.api.app:app --reload --port 2626

# Terminal 2
cd gui
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:2626`; `VITE_API_BASE_URL` can override the relative `/api/v1` client default.

Run the complete monorepo verification without combining environments or lockfiles:

```powershell
./scripts/verify.ps1
```

Architecture and component ownership are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
