# Phase 11 - API Search Adapters and Serialization

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Translate validated API schemas into the shared core search model and translate core search responses back to stable API JSON schemas without implementing search behavior in the API.

## Tasks

- [ ] Write the unit tests for simple-search adaptation before implementing it.
  - [ ] Add tests proving simple search maps the station fields to `GroundStation`.
  - [ ] Add tests proving simple search maps `window.start_at` to a timezone-aware core `SearchWindow`.
  - [ ] Add tests proving simple search uses `SatelliteGroup.ACTIVE`.
  - [ ] Add tests proving simple search applies culmination-altitude defaults of `[0, 90]` degrees.
  - [ ] Add tests proving simple search disables start, end, and culmination azimuth preferences.
  - [ ] Add tests proving simple search applies Sun-proximity defaults of `[0, 180]` degrees.
  - [ ] Add tests proving simple search applies satellite-altitude defaults of `[200, 2000] km`.
  - [ ] Add tests proving simple search applies `result_limit = 10`.
  - [ ] Add tests proving simple search applies `score_threshold = 0` as disabled threshold filtering.
  - [ ] Add tests proving simple search does not expose scoring configuration or workflow labels to the core.
- [ ] Write the unit tests for advanced-search adaptation before implementing it.
  - [ ] Add tests proving omitted `satellite_group` defaults to `SatelliteGroup.ACTIVE`.
  - [ ] Add tests proving supported satellite groups map to the correct core enum values.
  - [ ] Add tests proving culmination altitude range and target/tolerance criteria map to the core model.
  - [ ] Add tests proving start, end, and culmination azimuth criteria map independently.
  - [ ] Add tests proving Sun-proximity and satellite-altitude ranges map to the core model.
  - [ ] Add tests proving `result_limit` and `score_threshold` map to the core model.
  - [ ] Add tests proving omitted optional criteria remain disabled as `None` or the approved core default.
  - [ ] Add tests proving unsupported advanced fields are rejected by schema validation before adapter code runs.
- [ ] Write the unit tests for core response serialization before implementing it.
  - [ ] Add tests proving ranked core candidates serialize in rank order.
  - [ ] Add tests proving match scores, TLE lines, TLE epoch, and source group are preserved.
  - [ ] Add tests proving pass geometry times are serialized as UTC ISO 8601 strings.
  - [ ] Add tests proving pass geometry angles and metrics are preserved.
  - [ ] Add tests proving diagnostics are preserved.
  - [ ] Add tests proving a core `NO_RESULT` response serializes as `status: "no_result"` with an empty result list.
- [ ] Implement request adapters.
  - [ ] Add `simple_search_to_core_request()` or the approved equivalent.
  - [ ] Add `advanced_search_to_core_request()` or the approved equivalent.
  - [ ] Keep default values centralized so route handlers do not duplicate them.
  - [ ] Keep adapters deterministic and side-effect free.
  - [ ] Keep adapters from calling `search_candidates()`, loading TLE data, or touching station persistence.
- [ ] Implement response adapters.
  - [ ] Add `core_response_to_api_response()` or the approved equivalent.
  - [ ] Convert core enums to public string values.
  - [ ] Convert UTC datetimes to API datetime strings with explicit UTC reference.
  - [ ] Preserve candidate ranks assigned by the core.
  - [ ] Preserve response diagnostics without inventing API-only search metrics.
- [ ] Run the focused adapter tests.
  - [ ] Run simple-search adapter tests first.
  - [ ] Run advanced-search adapter tests next.
  - [ ] Run response serialization tests after request conversion passes.
  - [ ] Run the full unit suite after adapter implementation.

## Done When

- [ ] Simple search adapts station and window inputs into a complete core `SearchRequest` with API-defined defaults.
- [ ] Advanced search adapts only supported criteria into the shared core model.
- [ ] API response serialization preserves core result meaning, ranking, TLE data, geometry, metrics, and diagnostics.
- [ ] Adapters do not execute searches, load TLE data, or read/write station persistence.
