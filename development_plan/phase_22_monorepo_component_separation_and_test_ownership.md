# Phase 22 - Monorepo Component Separation and Test Ownership

> Mandatory rule: Always write or relocate the tests for a component before moving its implementation. After the first production-code move, do not change test behavior without permission; path and import updates required by the approved layout must already be complete.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage Core and API dependencies and commands with their own Poetry projects. Manage GUI dependencies and commands with npm and the committed npm lockfile.

> Repository rule: Keep one top-level Git repository. The three component directories are independently buildable projects, not nested Git repositories or submodules, and must not contain their own `.git` directories.

## Goal

Separate the current combined application into Core, API, and GUI projects inside the existing Git repository, with explicit dependency direction and tests owned and executed by the component whose behavior they verify.

Preserve the public Python imports `tlefinder.core` and `tlefinder.api` by using `tlefinder` as a shared implicit namespace. Preserve the existing HTTP contract and GUI behavior during this structural phase.

## Target Layout

```text
core/
  README.md
  pyproject.toml
  poetry.lock
  src/tlefinder/core/
  src/tlefinder/benchmarks/
  tests/unit/
  tests/functional/
  tests/fixtures/
api/
  README.md
  pyproject.toml
  poetry.lock
  src/tlefinder/api/
  tests/unit/
  tests/functional/
  tests/fixtures/
gui/
  README.md
  package.json
  package-lock.json
  src/
  tests/
README.md
.github/
  workflows/
    core.yml
    api.yml
    gui.yml
```

The Python distribution names are `tlefinder-core` and `tlefinder-api`. Their import paths remain `tlefinder.core` and `tlefinder.api`. Neither Python project owns `src/tlefinder/__init__.py`; this allows both distributions to contribute packages to the same PEP 420 namespace without installation-order conflicts.

## Tasks

- [x] Record the pre-migration baseline before changing paths.
  - [x] Run the complete existing Python unit suite and record the result.
  - [x] Run the existing API functional suite and record the result separately.
  - [x] Run the GUI type check and production build and record the result.
  - [x] Record the current Core and API coverage reports so the split cannot silently reduce coverage.
  - [x] Inventory every source module, test, fixture, entry point, dependency, environment variable, and documentation link that contains a path into the combined project.
- [x] Write the component-boundary tests before moving production code.
  - [x] Add a Core packaging test proving `tlefinder.core` imports when only the Core project is installed.
  - [x] Add an API packaging test proving `tlefinder.api` and `tlefinder.core` import when the API project and its declared Core dependency are installed.
  - [x] Add an installation-order test proving the shared `tlefinder` namespace works whether Core or API is installed first.
  - [x] Add a Core boundary test proving Core does not import API, GUI, FastAPI, Pydantic, YAML persistence, React, or Vite code.
  - [x] Add an API boundary test proving API depends on Core through public Core imports and never imports GUI code.
  - [x] Add a GUI boundary check proving GUI reaches search behavior only through the HTTP client and contains no copied Python search implementation.
  - [x] Add a repository-layout check that rejects nested `.git` directories and obsolete combined-project source or test paths.
- [x] Create an independent Core Python project.
  - [x] Create `core/pyproject.toml` with distribution name `tlefinder-core`.
  - [x] Declare only Core runtime dependencies, including `httpx`, `numpy`, `skyfield`, and `tzdata`.
  - [x] Declare Core test and benchmark development dependencies in the Core project only.
  - [x] Move `tlefinder.core` into `core/src/tlefinder/core` without changing its public behavior.
  - [x] Move `tlefinder.benchmarks` into `core/src/tlefinder/benchmarks` and keep `tlefinder-benchmark-core` as a Core entry point.
  - [x] Generate and commit a Core-specific Poetry lockfile.
  - [x] Confirm building the Core wheel does not include API or GUI files.
- [x] Create an independent API Python project.
  - [x] Create `api/pyproject.toml` with distribution name `tlefinder-api`.
  - [x] Declare `tlefinder-core` as an explicit local path dependency for monorepo development.
  - [x] Declare API-only runtime dependencies, including `fastapi`, `uvicorn`, and `pyyaml`.
  - [x] Declare API test dependencies in the API project only.
  - [x] Move `tlefinder.api` into `api/src/tlefinder/api` without changing routes, schemas, error envelopes, or serialization.
  - [x] Keep `tlefinder.api.app:app` as the Uvicorn application entry point.
  - [x] Generate and commit an API-specific Poetry lockfile.
  - [x] Confirm building the API wheel does not include Core source files or GUI assets; Core is supplied as a declared dependency.
- [x] Promote the GUI to an independent frontend project.
  - [x] Move the current Vite project from the Python package tree to `gui`.
  - [x] Preserve the `tlefinder-gui` package name, npm lockfile, TypeScript settings, Vite settings, source tree, and relative `/api/v1` default.
  - [x] Keep GUI runtime dependencies out of both Poetry projects.
  - [x] Add a GUI test command and the minimum Vitest and React Testing Library configuration needed for component-owned unit tests.
  - [x] Confirm the GUI can install, type-check, test, and build without either Python source tree being present under its directory.
- [x] Split existing tests by behavior ownership before moving the corresponding source.
  - [x] Move model, validation, time, TLE repository, pass analysis, filtering, scoring, ranking, engine, import-boundary, and benchmark tests to `core/tests`.
  - [x] Move Core search fixtures such as sample TLE files and TLE metadata to `core/tests/fixtures`.
  - [x] Move API schema, adapter, configuration, station-store, route, error, OpenAPI, and API functional tests to `api/tests`.
  - [x] Move or recreate only API-owned request, response, station-store, and mocked-Core fixtures under `api/tests`.
  - [x] Add GUI unit tests for API URL construction, request serialization, response handling, validation helpers, and the most important user workflows.
  - [x] Do not import fixtures, `conftest.py` files, test helpers, or private implementation details across component test suites.
  - [x] Keep Core/API integration assertions in the API suite because API is the consumer of the Core contract.
  - [x] Keep browser-facing GUI/API contract assertions in the GUI suite and execute them against a stub or test API without live TLE downloads.
- [x] Make test execution independent and deterministic.
  - [x] Configure each Poetry project so its default `pytest` command discovers only its own tests.
  - [x] Define Core `unit` and `functional` markers within the Core project.
  - [x] Define API `unit` and `functional` markers within the API project.
  - [x] Ensure Core tests never require FastAPI, a station YAML file, the GUI, Node.js, or network access.
  - [x] Ensure API tests replace Core search and external I/O at the API boundary where appropriate.
  - [x] Ensure GUI unit tests never require Python, a browser server, or live network access.
  - [x] Add component-specific coverage commands and fail if files outside the owning component are measured accidentally.
- [x] Replace combined-project developer orchestration.
  - [x] Remove the cross-component `tlefinder.dev` module from the Core/API distributions.
  - [x] Document separate local Core, API, and GUI setup and test commands in each component README.
  - [x] Document the temporary two-terminal API and GUI development workflow until the Docker Compose workflow is added in phase 23.
  - [x] Add top-level verification commands that run Core, API, and GUI checks without merging their environments or lockfiles.
  - [x] Add `.github/workflows/core.yml`, `.github/workflows/api.yml`, and `.github/workflows/gui.yml` with path-aware triggers.
  - [x] Make the API workflow run when either `api/**` or `core/**` changes because API consumes Core.
  - [x] Retain a full monorepo verification path for shared configuration and dependency-boundary changes.
- [x] Remove obsolete combined paths only after the split is green.
  - [x] Delete the former combined `tlefinder/src/tlefinder/core`, `tlefinder/src/tlefinder/api`, and nested GUI paths after their new owners pass all tests.
  - [x] Delete the former combined `tlefinder/tests` tree after every test and fixture has a recorded destination.
  - [x] Remove the former combined `tlefinder/pyproject.toml` and lockfile after the Core and API projects install reproducibly.
  - [x] Search source, tests, scripts, and documentation for stale paths, obsolete commands, and undeclared cross-component imports.
  - [x] Update architecture and contributor documentation with the final component tree and dependency rules.
- [x] Run final migration verification.
  - [x] Install Core from a clean environment and run all Core unit and functional tests.
  - [x] Install API and its local Core dependency from a separate clean environment and run all API unit and functional tests.
  - [x] Install GUI dependencies from the lockfile and run GUI tests, type checks, and the production build.
  - [x] Build both Python wheels and inspect their contents for ownership violations.
  - [x] Verify all previously supported CLI and Uvicorn entry points from the new project roots.
  - [x] Compare the post-migration results and coverage with the recorded baseline.

## Done When

- [x] The Git repository contains three independently buildable top-level projects under `core`, `api`, and `gui`, with no nested Git repositories.
- [x] Core has no runtime dependency on API or GUI, API explicitly depends on Core, and GUI communicates with API only over HTTP.
- [x] Core and API use separate Poetry manifests, lockfiles, virtual environments, and test configurations; GUI uses its own npm manifest and lockfile.
- [x] Every existing test and fixture has one documented component owner, and no component test suite imports another component's test code.
- [x] The `tlefinder.core` and `tlefinder.api` public import paths and existing HTTP behavior remain compatible.
- [x] Core tests, API tests, GUI tests, GUI type checks, GUI build, and package-boundary checks all pass from clean environments.
- [x] No obsolete combined-project paths or dependency declarations remain.
