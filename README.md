# TLE Finder

New application package for the reusable TLE Finder core search engine.

Run local tests with:

```powershell
poetry run pytest
```

Start the API first, then the GUI dev server with:

```powershell
poetry install
poetry run tlefinder-dev
```

Pass `--api-reload` when you want uvicorn reload enabled.

Poetry uses the Python interpreter selected by `pyenv global`; on this
workspace that is Python 3.10.

## Core Request Construction

GUI, API, and Python callers must construct `tlefinder.core.SearchRequest`
before calling the core workflow. The shared request must contain:

- `GroundStation(latitude, longitude, elevation_m)` using decimal degrees and meters.
- `SearchWindow(start_at, duration_minutes)` where `start_at` is a timezone-aware `datetime`. Use `timezone.utc` or an explicit fixed UTC offset; timezone-name objects such as `zoneinfo.ZoneInfo` must be converted by adapters before constructing the core request. Never infer timezone from the station location.
- `SearchCriteria(...)` using only the phase 2 criteria fields: culmination altitude, azimuth targets with tolerances, Sun proximity, satellite altitude, `score_threshold`, and `result_limit`.
- `SatelliteGroup.ACTIVE`, `SatelliteGroup.VISUAL`, or `SatelliteGroup.AMATEUR` to select the TLE source group.

Magnitude and object-type filters are intentionally not part of the active
phase 2 request contract. Diagnostics returned by core models are plain
JSON-friendly dictionaries with stable snake_case keys.

## Parallel Search Modes

Exact serial search is the default. API deployments can opt in to process-pool
parallel search with `TLEFINDER_PARALLEL_SEARCH_ENABLED=true`; the conservative
enabled defaults are `4` workers and chunk size `32`. Simple active searches may
use approximate budgeted parallel mode when server-side parallel execution is
enabled and no strict hard filters are present.

Benchmark evidence and operational guidance are recorded in
[docs/PHASE_21_PARALLEL_SEARCH_BENCHMARKS.md](docs/PHASE_21_PARALLEL_SEARCH_BENCHMARKS.md).
