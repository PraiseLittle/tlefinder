# Phase 8 - API Foundation and Dependency Boundary

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Create the import-safe FastAPI API package foundation described by `APIArchitecture.md`, while proving the dependency direction before adding business behavior.

## Tasks

- [ ] Write the unit tests for the API package foundation before implementing it.
  - [ ] Add tests proving `tlefinder.api` imports without importing GUI modules.
  - [ ] Add tests proving the core package does not import `fastapi`, `pydantic`, `yaml`, or `tlefinder.api`.
  - [ ] Add tests proving `create_app()` returns a FastAPI application with the expected title, version, and route prefix conventions.
  - [ ] Add tests proving a custom `ApiSettings` object can be attached to app state.
  - [ ] Add tests proving the default settings resolve a backend-controlled station YAML path without placing persistence inside `tlefinder.core`.
- [ ] Add the API runtime and test dependencies.
  - [ ] Add `fastapi>=0.115,<1.0` to runtime dependencies.
  - [ ] Add `uvicorn[standard]>=0.30,<1.0` to runtime dependencies.
  - [ ] Add `pyyaml>=6.0,<7.0` to runtime dependencies.
  - [ ] Confirm the test client dependency path is available through `httpx` or FastAPI's supported test stack.
  - [ ] Run dependency installation through Poetry and keep lockfile changes scoped to the API requirements.
- [ ] Create the API package skeleton.
  - [ ] Create `tlefinder/src/tlefinder/api/__init__.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/app.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/config.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/errors.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/schemas.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/adapters.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/station_store.py`.
  - [ ] Create `tlefinder/src/tlefinder/api/routers/__init__.py`.
  - [ ] Create placeholder router modules for `search.py` and `stations.py`.
- [ ] Implement API configuration.
  - [ ] Add `ApiSettings` with `station_store_path: Path`.
  - [ ] Read `TLEFINDER_STATION_STORE_PATH` when it is set.
  - [ ] Use a documented backend-controlled default station store path when the environment variable is absent.
  - [ ] Keep configuration independent from GUI settings and core models.
- [ ] Implement the app factory shell.
  - [ ] Add `create_app(settings: ApiSettings | None = None) -> FastAPI`.
  - [ ] Attach the resolved settings to `app.state`.
  - [ ] Add the module-level `app = create_app()` entrypoint for Uvicorn.
  - [ ] Register empty `/api/v1` routers only after the router modules exist.
  - [ ] Keep all route handlers behavior-free in this phase.
- [ ] Run the focused foundation tests.
  - [ ] Run the API import and dependency-boundary tests.
  - [ ] Run the existing core import tests to confirm no FastAPI dependency leaked into the core.
  - [ ] Run the full unit suite after the foundation modules are in place.

## Done When

- [ ] `tlefinder.api` exists and can be imported without GUI dependencies.
- [ ] `create_app()` returns a FastAPI app with settings attached to `app.state`.
- [ ] API dependencies are declared through Poetry.
- [ ] The core package still has no dependency on API, FastAPI, Pydantic, or YAML persistence modules.
- [ ] The focused API foundation tests and existing core unit tests pass.
