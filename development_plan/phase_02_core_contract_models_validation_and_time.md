# Phase 2 - Core Contract, Models, Validation, and Time

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Define the shared request and response contract of the core engine and lock down the validation and time rules that every interface must respect.

## Tasks

- [x] Write the unit tests for the core contract before implementing it.
  - [x] Add tests for valid and invalid ground-station coordinates.
  - [x] Add tests for search-window duration limits and timezone-awareness requirements.
  - [x] Add tests for range-constraint consistency and score-threshold bounds.
  - [x] Add tests proving that equivalent UTC and local-time inputs normalize to the same UTC interval.
- [x] Implement the shared domain models in `models.py`.
  - [x] Add the enums for satellite grouping and response status.
  - [x] Add the dataclasses for `GroundStation`, `SearchWindow`, `RangeConstraint`, `TargetToleranceConstraint`, `SearchCriteria`, `SearchRequest`, `TleRecord`, `SatelliteRecord`, `PassGeometry`, `PassMetrics`, `CandidatePass`, and `SearchResponse`.
  - [x] Keep magnitude and object-type criteria out of the active phase 2 request, validation, filtering, and scoring contract.
  - [x] Reserve `PassMetrics.magnitude | None` in phase 2 so the frozen core contract already matches the architecture, but keep it inactive and unset in this increment.
  - [x] Decide and document a stable diagnostics structure so adapters can expose useful failure details.
- [x] Implement the typed exceptions in `errors.py`.
  - [x] Add `ValidationError`, `TleFreshnessError`, `TleLoadError`, `PropagationError`, and `SearchExecutionError`.
  - [x] Make the error messages precise enough to be surfaced by GUI and API adapters.
- [x] Implement request validation in `validation.py`.
  - [x] Validate the full request structure through `validate_search_request()`.
  - [x] Validate ground-station ranges, including numeric elevation checks.
  - [x] Validate the 30-minute maximum duration and the explicit timezone requirement.
  - [x] Validate culmination, azimuth, Sun-proximity, satellite-altitude, threshold, and result-limit constraints.
  - [x] Do not accept magnitude or object-type request criteria in phase 2.
- [x] Implement time normalization in `time_utils.py`.
  - [x] Add `normalize_start_time_to_utc()`.
  - [x] Add `build_search_interval()`.
  - [x] Ensure no timezone is inferred from the station location.
- [x] Define the public construction rules for adapters.
  - [x] Document how GUI, API, and Python callers must build `SearchRequest`.
  - [x] Make the new core package importable without pulling Flask or template dependencies.

## Done When

- [x] A valid `SearchRequest` can be created and validated entirely inside the core package.
- [x] Equivalent UTC and local-time requests produce the same normalized interval.
- [x] Invalid requests fail fast with typed validation errors and deterministic messages.
