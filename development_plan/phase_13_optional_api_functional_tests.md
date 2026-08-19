# Phase 13 - Optional API Functional Tests

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Optionally add higher-level functional tests that exercise the completed API through HTTP-like calls, temporary station persistence, and controlled core-search doubles.

## Tasks

- [ ] Decide whether to run this optional phase.
  - [ ] Confirm that phases 8 through 12 have passing unit coverage.
  - [ ] Confirm that functional tests are useful for the current release scope.
  - [ ] Keep this phase deferred if route-level unit tests already provide sufficient confidence for the current milestone.
- [ ] Write the functional tests for OpenAPI before changing any implementation.
  - [ ] Add tests proving `/openapi.json` is reachable from a created app.
  - [ ] Add tests proving all station and search routes are listed in the generated OpenAPI document.
  - [ ] Add tests proving request, response, and error schema components are present.
  - [ ] Add tests proving unsupported fields are documented as rejected by the generated schemas where practical.
- [ ] Write the functional tests for station routes before changing any implementation.
  - [ ] Add tests proving `GET /api/v1/stations` creates and returns an empty list with a temporary missing YAML file.
  - [ ] Add tests proving `PUT /api/v1/stations` persists a valid station list and a later `GET` returns it.
  - [ ] Add tests proving invalid station-list updates return `422` and preserve the previous persisted list.
  - [ ] Add tests proving malformed persisted YAML returns a machine-readable store error.
  - [ ] Add tests proving station store paths are isolated per test through `ApiSettings`.
- [ ] Write the functional tests for simple search before changing any implementation.
  - [ ] Add tests proving a valid simple-search request returns HTTP `200` with ranked results from a controlled core response.
  - [ ] Add tests proving simple-search defaults are visible in the core request captured by the controlled search function.
  - [ ] Add tests proving simple-search no-result returns HTTP `200`, `status: "no_result"`, and an empty result list.
  - [ ] Add tests proving a named station from a successful simple search is persisted after the search.
  - [ ] Add tests proving an invalid simple-search request does not call core search.
- [ ] Write the functional tests for advanced search before changing any implementation.
  - [ ] Add tests proving supported advanced criteria are mapped into the captured core request.
  - [ ] Add tests proving unsupported advanced criteria return `422`.
  - [ ] Add tests proving candidate-selection threshold and result limit are passed to the core model.
  - [ ] Add tests proving supported satellite groups are accepted.
  - [ ] Add tests proving invalid satellite groups return a machine-readable validation error.
- [ ] Write the functional tests for operational error behavior before changing any implementation.
  - [ ] Add tests proving core validation errors return `422`.
  - [ ] Add tests proving TLE load and freshness errors return `503`.
  - [ ] Add tests proving search execution errors return `500`.
  - [ ] Add tests proving station persistence failure after a successful search returns an explicit persistence error.
  - [ ] Add tests proving unexpected errors return a generic `internal_error` payload.
- [ ] Adjust implementation only if functional tests expose real integration gaps.
  - [ ] Do not rewrite unit tests after code changes without explicit permission.
  - [ ] Keep fixes scoped to route wiring, serialization, exception mapping, or test app configuration.
  - [ ] Do not add search behavior to the API to satisfy functional tests.
  - [ ] Preserve the strict core/API dependency boundary.
- [ ] Run the API functional test suite.
  - [ ] Run OpenAPI functional tests first.
  - [ ] Run station-route functional tests next.
  - [ ] Run search-route functional tests after station persistence is stable.
  - [ ] Run operational error functional tests last.
  - [ ] Run all unit tests and selected functional tests together before closing the phase.

## Done When

- [ ] The optional functional test suite provides HTTP-level confidence for the completed API.
- [ ] Temporary station-store files make functional tests isolated and repeatable.
- [ ] Search functional tests use controlled core responses instead of live TLE downloads.
- [ ] Functional tests do not duplicate all unit cases, only the cross-module behavior that matters.
- [ ] Any implementation fixes from this phase preserve the API as a thin adapter over the core.
