# TLE Finder

New application package for the reusable TLE Finder core search engine.

Run local tests with:

```powershell
poetry run pytest
```

Poetry uses the Python interpreter selected by `pyenv global`; on this
workspace that is Python 3.10.

## Core Request Construction

GUI, API, and Python callers must construct `tlefinder.core.SearchRequest`
before calling the core workflow. The shared request must contain:

- `GroundStation(latitude, longitude, elevation_m)` using decimal degrees and meters.
- `SearchWindow(start_at, duration_minutes)` where `start_at` is a timezone-aware `datetime`. Use `timezone.utc`, a `zoneinfo.ZoneInfo` name, or an explicit UTC offset; never infer timezone from the station location.
- `SearchCriteria(...)` using only the phase 2 criteria fields: culmination altitude, azimuth targets with tolerances, Sun proximity, satellite altitude, `score_threshold`, and `result_limit`.
- `SatelliteGroup.ACTIVE`, `SatelliteGroup.VISUAL`, or `SatelliteGroup.AMATEUR` to select the TLE source group.

Magnitude and object-type filters are intentionally not part of the active
phase 2 request contract. Diagnostics returned by core models are plain
JSON-friendly dictionaries with stable snake_case keys.
