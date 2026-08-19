# Phase 22 Baseline and Ownership Inventory

Captured on 2026-08-19 before any production path was moved. The local toolchain was the global `pyenv` selection Python 3.10.11, Poetry 2.3.4, Node.js 22.12.0, and npm 10.9.0.

## Pre-migration verification

| Check | Result |
| --- | --- |
| Combined Python unit suite | 414 passed in 14.78 seconds |
| API functional suite | 31 passed in 3.30 seconds |
| Core and benchmark coverage | 249 passed; 80% total (1,793 statements, 572 branches) |
| API coverage | 195 passed; 94% total (642 statements, 106 branches) |
| GUI type check | Passed |
| GUI production build | Passed; 46 modules transformed |

The machine-readable baseline coverage reports are in `development_plan/phase_22_evidence/baseline-core-coverage.json` and `development_plan/phase_22_evidence/baseline-api-coverage.json`.

## Source and ownership inventory

- Core source: `core`, comprising `__init__`, `engine`, `errors`, `filtering`, `models`, `pass_analysis`, `ranking`, `scoring`, `time_utils`, `tle_repository`, and `validation`.
- Core benchmark source: `benchmarks.__init__` and `benchmarks.core_search`.
- API source: `api.__init__`, `adapters`, `app`, `config`, `errors`, `schemas`, `station_store`, and routers `search` and `stations`.
- GUI source: the Vite entry point and styles; typed API client and schemas; form, formatting, and validation helpers; and the React application/component tree.
- Obsolete cross-component source: `tlefinder.dev`, which launched API and GUI together.

## Test and fixture destinations

- Core owns the 11 existing model, validation, time, repository, pass-analysis, filtering, scoring, ranking, engine, import, and benchmark unit test modules under `core/tests/unit`.
- Core owns `active_sample.tle`, `visual_sample.tle`, `amateur_sample.tle`, and `tle_metadata.json` under `core/tests/fixtures`, plus the domain object factories in `core/tests/conftest.py`.
- API owns the seven existing schema, adapter, foundation, station-store, station-route, search-route, and error/OpenAPI unit modules under `api/tests/unit`.
- API owns the four existing HTTP functional modules and their request, response, station-store, and mocked-Core fixtures under `api/tests/functional`.
- GUI owns API-client, request-validation, primary-workflow, and component-boundary tests under `gui/tests`; these use a stubbed fetch/API client and never make live requests.
- No destination imports another component's `conftest.py`, fixtures, or private test helpers.

## Entry points, dependencies, and configuration

- Existing entry points: `tlefinder-benchmark-core`, retained by Core; `tlefinder-dev`, removed; and `tlefinder.api.app:app`, retained as the Uvicorn application.
- Core runtime dependencies: `httpx`, `numpy`, `skyfield`, and `tzdata`. Core development dependencies: `pytest` and `pytest-cov`.
- API runtime dependencies: local `tlefinder-core`, `fastapi`, `pydantic`, `uvicorn[standard]`, and `pyyaml`. API development dependencies: `httpx`, `pytest`, and `pytest-cov`.
- GUI runtime dependencies: `react` and `react-dom`; Vite, TypeScript, Vitest, jsdom, and React Testing Library are GUI-only development dependencies.
- API environment variables: `TLEFINDER_STATION_STORE_PATH`, `TLEFINDER_PARALLEL_SEARCH_ENABLED`, `TLEFINDER_PARALLEL_WORKER_COUNT`, and `TLEFINDER_PARALLEL_CHUNK_SIZE`.
- GUI environment variable: `VITE_API_BASE_URL`; the default remains relative `/api/v1`.

## Pre-migration path references

Current documentation with combined paths comprised the combined `tlefinder/README.md`, `docs/ARCHITECTURE.md`, `docs/APIArchitecture.md`, and the nested GUI README plus API-client/type comments. Historical phase plans also record the layout that existed when those phases were implemented. Current architecture and contributor instructions are updated as part of Phase 22; historical plans remain historical evidence.

## Post-migration verification

Captured on 2026-08-19 after the obsolete combined source, test, and project paths were removed from the repository:

| Check | Result | Baseline comparison |
| --- | --- | --- |
| Core default suite | 258 passed | All 249 original Core tests retained; packaging and boundary checks added |
| Core and benchmark coverage | 80.21% (1,793 statements, 572 branches) | Exactly unchanged |
| API default suite | 199 passed | All 195 original API tests retained; ownership, packaging, and namespace checks added |
| API coverage | 93.58% (642 statements, 106 branches) | Exactly unchanged |
| Core-only installation | Passed from the built `tlefinder-core` wheel | New boundary proof |
| Core-first/API-first installation | Both orders passed from built wheels | New PEP 420 namespace proof |
| GUI lockfile install and tests | `npm ci`; 9 tests passed | New component-owned suite |
| GUI type check and build | Passed; 46 modules transformed | Same production output ownership |
| Wheel ownership inspection | Both wheels passed | No cross-component package files |
| Entrypoints | Benchmark command and `tlefinder.api.app:app` passed; `tlefinder-dev` absent | Supported entries preserved |

The post-migration reports are `development_plan/phase_22_evidence/post-core-coverage.json` and `development_plan/phase_22_evidence/post-api-coverage.json`. Coverage thresholds are pinned to the exact baseline percentages and measurement is scoped to the owning package.

The former combined tree, including untracked archive, JSON, logs, caches, and generated environments, was preserved outside the repository at `C:\Users\jda\Work\TLEfinder-phase22-legacy-20260819` rather than irreversibly deleted.
