# Phase 3 - TLE Repository and Dataset Management

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Build the data-loading layer that owns TLE download, caching, parsing, freshness checks, and the preparation of satellite records for the search engine.

## Tasks

- [ ] Write the unit tests for the repository layer before implementing it.
  - [ ] Add tests for parsing valid sample TLE files into `TleRecord` objects.
  - [ ] Add tests for stale-dataset rejection when the data is older than 24 hours.
  - [ ] Add tests for cache reuse when a fresh local file already exists.
  - [ ] Add tests for retrieval failures and malformed-file failures with typed errors.
- [ ] Create deterministic fixture data for repository tests.
  - [ ] Add representative `active`, `visual`, and `amateur` sample TLE files under `tlefinder/tests/fixtures`.
  - [ ] Add fixture metadata describing expected catalog numbers, names, and epochs.
  - [ ] Ensure all unit tests run offline without live network access.
- [ ] Implement `tle_repository.py`.
  - [ ] Add `download_tle_dataset()` with one explicit source configuration per supported satellite group.
  - [ ] Add `parse_tle_file()` and convert each entry into a typed `TleRecord`.
  - [ ] Add `build_satellite_records()` so later phases consume one shared structure.
  - [ ] Add `is_tle_fresh()` using the 24-hour non-functional requirement.
  - [ ] Add `load_tle_dataset()` as the only public repository entrypoint used by the engine.
- [ ] Centralize repository configuration and failure handling.
  - [ ] Keep cache locations and source URLs inside the repository layer, not in the engine.
  - [ ] Make the freshness failure an explicit error rather than a no-result response.
  - [ ] Make the repository testable through dependency injection or overridable paths where needed.
- [ ] Defer classification metadata that is not needed by the phase 3 repository.
  - [ ] Keep object-type loading out of this phase because object-type support is deferred beyond the frozen core increment.
  - [ ] Keep repository records focused on TLE data, satellite identity, source group, and freshness.

## Done When

- [ ] Fresh sample datasets load into typed satellite records without using the network.
- [ ] Stale data stops the workflow with `TleFreshnessError`.
- [ ] The repository exposes one stable loading entrypoint for the engine.
