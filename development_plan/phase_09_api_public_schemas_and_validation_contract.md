# Phase 9 - API Public Schemas and Validation Contract

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Define the public JSON request, response, and error contracts for the API using Pydantic models, with strict validation for unsupported fields and HTTP-specific input rules.

## Tasks

- [x] Write the unit tests for public schema validation before implementing it.
  - [x] Add tests proving station schemas require valid numeric latitude, longitude, and elevation values.
  - [x] Add tests proving persisted station entries require a non-empty trimmed name.
  - [x] Add tests proving search-request stations may omit a name when no persistence is needed.
  - [x] Add tests proving `window.start_at` accepts ISO 8601 values with `Z` or an explicit UTC offset.
  - [x] Add tests proving `window.start_at` rejects missing, invalid, or unsupported UTC offsets.
  - [x] Add tests proving `duration_minutes` must be greater than `0` and no greater than `30`.
  - [x] Add tests proving range constraints reject out-of-bound values and `minimum > maximum`.
  - [x] Add tests proving azimuth target/tolerance constraints reject invalid targets and invalid tolerances.
  - [x] Add tests proving `result_limit` is a strictly positive integer and rejects booleans, floats, and strings.
  - [x] Add tests proving `score_threshold` is numeric and within `[0, 100]`.
  - [x] Add tests proving simple-search requests reject advanced criteria, thresholds, result limits, scoring configuration, and unknown fields.
  - [x] Add tests proving advanced-search requests reject unsupported active criteria through `extra="forbid"`.
- [x] Write the unit tests for response and error schemas before implementing them.
  - [x] Add tests proving result responses support ranked candidates, TLE data, geometry, metrics, diagnostics, and `status: "results"`.
  - [x] Add tests proving no-result responses use HTTP-success payload semantics with `status: "no_result"` and an empty `results` list.
  - [x] Add tests proving all response datetimes serialize with an explicit UTC reference.
  - [x] Add tests proving error responses use the stable `{"error": ...}` envelope.
  - [x] Add tests proving field errors include both a field path and a readable message.
- [x] Implement common schema settings.
  - [x] Use Pydantic v2 style models if the dependency set supports it.
  - [x] Configure request models to reject unsupported fields where required by `APIRequirement.md`.
  - [x] Use strict validation where practical so booleans are not accepted as numeric inputs.
  - [x] Keep public schema names stable for generated OpenAPI output.
- [x] Implement request schemas.
  - [x] Add station schemas for persisted stations and search-input stations.
  - [x] Add the search-window schema with explicit-offset datetime validation.
  - [x] Add reusable range and target/tolerance constraint schemas.
  - [x] Add simple-search request schema with only station and window inputs.
  - [x] Add advanced-search request schema with supported criteria and optional satellite group.
  - [x] Keep scoring configuration, scoring weights, and ranking internals out of every request schema.
- [x] Implement response schemas.
  - [x] Add TLE response schema with name, lines, epoch UTC, and source group.
  - [x] Add satellite response schema.
  - [x] Add pass geometry response schema.
  - [x] Add metrics and diagnostics response schemas.
  - [x] Add search response schema for `results` and `no_result` states.
  - [x] Add station list response schema.
- [x] Implement error schemas.
  - [x] Add stable API error codes from `APIArchitecture.md`.
  - [x] Add field-error schema.
  - [x] Add error-envelope schema.
  - [x] Keep error models independent from FastAPI exception handlers, which are implemented later.
- [x] Run the focused schema tests.
  - [x] Run the schema validation tests first.
  - [x] Run the schema serialization tests next.
  - [x] Run the full unit suite after schema implementation.

## Done When

- [x] API request schemas enforce all validation rules that belong at the HTTP boundary.
- [x] Simple search accepts only station and window inputs.
- [x] Advanced search accepts only the supported criteria listed in `APIRequirement.md`.
- [x] Response and error schema tests pass with stable machine-readable shapes.
- [x] No schema imports GUI modules or calls the core search engine.
