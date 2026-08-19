# Phase 12 - API Routes, Errors, and OpenAPI Contract

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Wire the versioned HTTP routes, exception handlers, and OpenAPI metadata so the API can serve station management and search execution as a thin adapter over the core workflow.

## Tasks

- [ ] Write the unit tests for station routes before implementing them.
  - [ ] Add tests proving `GET /api/v1/stations` calls the station store and returns the persisted list.
  - [ ] Add tests proving `GET /api/v1/stations` creates an empty station list on first access through the store.
  - [ ] Add tests proving `PUT /api/v1/stations` replaces the complete station list with valid input.
  - [ ] Add tests proving invalid station replacement returns a machine-readable `422` response.
  - [ ] Add tests proving station load/create/save failures return a machine-readable `500` response.
- [ ] Write the unit tests for search routes before implementing them.
  - [ ] Add tests proving `POST /api/v1/search/simple` adapts the request and calls `tlefinder.core.search_candidates()`.
  - [ ] Add tests proving `POST /api/v1/search/advanced` adapts the request and calls `tlefinder.core.search_candidates()`.
  - [ ] Add tests proving no route implements pass detection, filtering, scoring, ranking, orbit propagation, or TLE freshness logic.
  - [ ] Add tests proving no-result core responses return HTTP `200` with `status: "no_result"`.
  - [ ] Add tests proving named stations are persisted only after successful search execution.
  - [ ] Add tests proving unnamed search stations are not persisted.
  - [ ] Add tests proving persistence failure after a successful search returns an explicit machine-readable persistence error.
- [ ] Write the unit tests for exception mapping before implementing it.
  - [ ] Add tests proving Pydantic request validation errors map to `422` and `validation_error`.
  - [ ] Add tests proving core `ValidationError` maps to `422` and `validation_error`.
  - [ ] Add tests proving station validation errors map to `422` and `station_validation_error`.
  - [ ] Add tests proving station store errors map to `500` and `station_store_error`.
  - [ ] Add tests proving core TLE load errors map to `503` and `tle_unavailable`.
  - [ ] Add tests proving core TLE freshness errors map to `503` and `tle_stale`.
  - [ ] Add tests proving core search execution errors map to `500` and `search_execution_error`.
  - [ ] Add tests proving unexpected exceptions map to `500` and `internal_error` without leaking traceback text.
- [ ] Write the unit tests for OpenAPI registration before implementing it.
  - [ ] Add tests proving `/openapi.json` contains `GET /api/v1/stations`.
  - [ ] Add tests proving `/openapi.json` contains `PUT /api/v1/stations`.
  - [ ] Add tests proving `/openapi.json` contains `POST /api/v1/search/simple`.
  - [ ] Add tests proving `/openapi.json` contains `POST /api/v1/search/advanced`.
  - [ ] Add tests proving public request, response, and error schemas are present with stable names.
- [ ] Implement exception handling.
  - [ ] Register FastAPI exception handlers from `errors.py`.
  - [ ] Normalize validation failures into the documented error envelope.
  - [ ] Map expected core and station-store exceptions to stable API error codes.
  - [ ] Preserve useful field-level error details when available.
  - [ ] Keep unexpected errors generic for clients.
- [ ] Implement station routes.
  - [ ] Add `GET /api/v1/stations`.
  - [ ] Add `PUT /api/v1/stations`.
  - [ ] Keep route handlers small and delegate persistence behavior to `station_store.py`.
  - [ ] Return schema objects rather than raw dictionaries where practical.
- [ ] Implement search routes.
  - [ ] Add `POST /api/v1/search/simple`.
  - [ ] Add `POST /api/v1/search/advanced`.
  - [ ] Convert request schemas through `adapters.py`.
  - [ ] Call `tlefinder.core.search_candidates()` exactly once for valid requests.
  - [ ] Persist named stations after successful search execution.
  - [ ] Convert core responses through `adapters.py`.
- [ ] Finalize app registration and OpenAPI metadata.
  - [ ] Register station and search routers under `/api/v1`.
  - [ ] Add route tags for `stations` and `search`.
  - [ ] Declare expected error responses in route metadata.
  - [ ] Include examples for simple search, advanced search, station list, no-result search, and error responses where practical.
- [ ] Run the focused route and integration-unit tests.
  - [ ] Run route tests with mocked station store and mocked core search first.
  - [ ] Run exception-mapping tests next.
  - [ ] Run OpenAPI contract tests after all routes are registered.
  - [ ] Run the full unit suite before moving to functional tests.

## Done When

- [ ] All four public API routes are registered under `/api/v1`.
- [ ] Search routes call the core search workflow instead of implementing satellite-search behavior.
- [ ] Station routes delegate persistence behavior to the station store.
- [ ] Expected validation, persistence, TLE, and search failures return stable machine-readable errors.
- [ ] `/openapi.json` exposes the public API contract with stable schema names.
- [ ] The full unit suite passes.
