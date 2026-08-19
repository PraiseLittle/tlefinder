# Phase 10 - API Station Persistence

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Implement the API-owned YAML optical ground station store with full validation, duplicate detection, first-access creation, and atomic replacement behavior.

## Tasks

- [x] Write the unit tests for station-store creation and loading before implementing it.
  - [x] Add tests proving first access creates parent directories and an empty YAML station list.
  - [x] Add tests proving an existing valid YAML file is loaded into station schemas.
  - [x] Add tests proving malformed YAML returns a station-store error instead of leaking parser details.
  - [x] Add tests proving missing required YAML fields return a machine-readable station-store error.
  - [x] Add tests proving the core package never reads from or writes to the station YAML file.
- [x] Write the unit tests for station-list validation before implementing it.
  - [x] Add tests proving invalid latitude, longitude, elevation, and names are rejected.
  - [x] Add tests proving duplicate physical stations in a submitted replacement list are rejected.
  - [x] Add tests proving duplicate station names with different coordinates are rejected.
  - [x] Add tests proving duplicate detection normalizes latitude, longitude, and elevation to the first five decimal digits.
  - [x] Add tests covering positive and negative coordinate truncation toward zero.
  - [x] Add tests proving a persisted list cannot contain more than one name for the same physical station.
- [x] Write the unit tests for write safety before implementing it.
  - [x] Add tests proving valid replacement writes the submitted list.
  - [x] Add tests proving invalid replacement preserves the previous persisted file.
  - [x] Add tests proving write failures preserve the previous persisted file.
  - [x] Add tests proving atomic replacement writes through a temporary file in the same directory.
  - [x] Add tests proving temporary files are cleaned up after failures when possible.
- [x] Write the unit tests for named search-station persistence before implementing it.
  - [x] Add tests proving an unnamed search station is not persisted.
  - [x] Add tests proving a new named search station is appended after a successful search route asks for persistence.
  - [x] Add tests proving equivalent coordinates with a different submitted name preserve the existing persisted station name.
  - [x] Add tests proving an exact duplicate station is not appended twice.
- [x] Implement station-store errors.
  - [x] Add API-specific station validation and store exception classes.
  - [x] Preserve enough field information for later HTTP error mapping.
  - [x] Keep exceptions independent from FastAPI route handlers.
- [x] Implement YAML persistence.
  - [x] Add `ensure_store_exists()` or the approved equivalent first-access helper.
  - [x] Add `load_stations()` for reading the complete list.
  - [x] Add `replace_stations()` for validating and atomically replacing the complete list.
  - [x] Add `add_station_if_new()` for named stations submitted through successful searches.
  - [x] Keep the YAML shape compatible with `APIArchitecture.md`.
- [x] Implement duplicate detection.
  - [x] Normalize latitude, longitude, and elevation by truncating toward zero to five decimal places.
  - [x] Compare normalized triples as physical station keys.
  - [x] Preserve the existing persisted name when a new named search station matches existing physical coordinates.
  - [x] Reject replacement lists that would create ambiguous names or physical duplicates.
- [x] Run the focused station-store tests.
  - [x] Run station-store validation tests first.
  - [x] Run station-store write-safety tests next.
  - [x] Run the full API unit suite after persistence is implemented.

## Done When

- [x] The API creates the station YAML file on first access.
- [x] Invalid station-list updates never corrupt or replace the previous file.
- [x] Duplicate station rules from `APIRequirement.md` are covered by tests and enforced.
- [x] Named station persistence can add new stations while preserving existing names for equivalent coordinates.
- [x] The core remains free of station persistence imports and file access.
