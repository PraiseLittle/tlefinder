# TLE Finder Monorepo

TLE Finder is one Git repository containing three independently buildable projects:

- `core/` — the `tlefinder-core` Python distribution and benchmark command.
- `api/` — the `tlefinder-api` Python distribution and FastAPI application.
- `gui/` — the `tlefinder-gui` Vite/React frontend.

Dependency direction is one way: API depends on Core through the public `tlefinder.core` contract, and GUI communicates with API only over HTTP. Core never depends on API or GUI. The two Python distributions share the implicit PEP 420 `tlefinder` namespace, so the public imports remain `tlefinder.core` and `tlefinder.api` without either project owning `src/tlefinder/__init__.py`.

## Container quick start

Docker Desktop can run the complete application with one Compose command from the repository root:

```powershell
docker compose up --detach --build --wait
```

Open `http://127.0.0.1:2627`. Compose starts the API first, waits for `/healthz`, then starts the GUI and connects both services through their private network. To expose the API on loopback for Swagger, use:

```powershell
docker compose -f compose.yaml -f compose.api-port.yaml up --detach --build --wait
```

Swagger is then available at `http://127.0.0.1:2626/docs`. Docker keeps stations and downloaded TLE datasets in separate named volumes, so both survive container recreation and image rebuilds. See [docs/CONTAINERS.md](docs/CONTAINERS.md) for logs, updates, configuration, volume backup and restore, resource limits, and troubleshooting.

## Local development

Install each component once, then use the combined launcher from the repository root:

```powershell
cd api
poetry install
cd ../gui
npm ci
cd ..
./scripts/dev.ps1
```

Open `http://127.0.0.1:2627`. The launcher keeps both processes in the same terminal; press Ctrl+C to stop them together. It reports a clear error if Docker or another process is already using port `2626` or `2627`.

To run the components independently, start `poetry run uvicorn tlefinder.api.app:app --reload --port 2626` from `api/` and `npm run dev` from `gui/` in separate terminals. Vite proxies `/api` to `http://127.0.0.1:2626`; `VITE_API_BASE_URL` can override the relative `/api/v1` client default.

Run the complete monorepo verification without combining environments or lockfiles:

```powershell
./scripts/verify.ps1
```

Architecture and component ownership are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
