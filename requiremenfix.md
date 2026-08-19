# Requirements Fix Plan

Use this checklist to track the cleanup of the overall application, API, and GUI requirements.

## Overall Requirement Fixes

- [x] Replace the placeholder GUI requirements in `REQUIREMENT.md` with concrete parent-level requirements for:
  - [x] optical ground station list management
  - [x] simple search workflow
  - [x] advanced search workflow

- [x] Define simple search behavior in `REQUIREMENT.md`, including:
  - [x] required inputs
  - [x] default behavior for criteria not provided by the user
  - [x] default candidate limit
  - [x] default candidate-selection threshold
  - [x] default ranking rule
  - [x] match-score meaning when no advanced criteria are provided

- [x] Make match-score requirements testable by defining:
  - [x] score range
  - [x] score interpretation
  - [x] scoring inputs
  - [x] tie-break behavior
  - [x] threshold range and validation

- [x] Decide whether optical ground station persistence is a parent-level requirement:
  - [x] confirm whether the API owns persistence
  - [x] confirm whether persistence must use a backend-controlled file
  - [x] define behavior when loading or saving the station list fails
  - [x] define whether search requests may use stations not present in the persisted list

- [x] Add concrete validation rules for:
  - [x] latitude
  - [x] longitude
  - [x] elevation
  - [x] azimuth values
  - [x] apparent altitude
  - [x] satellite altitude
  - [x] Sun proximity
  - [x] search-window duration
  - [x] result count
  - [x] candidate-selection threshold

- [x] Define accepted time input behavior:
  - [x] UTC datetime format
  - [x] local datetime format
  - [x] accepted UTC offsets
  - [x] output time reference

- [x] Define TLE and auxiliary data requirements:
  - [x] TLE freshness rule
  - [x] behavior when fresh TLE data is unavailable

- [x] Define pass-detection criteria:
  - [x] pass start rule
  - [x] pass end rule
  - [x] culmination rule
  - [x] minimum sampling or propagation precision expectations
  - [x] edge cases at search-window boundaries

## API Requirement Fixes

- [x] Update `APIRequirement.md` after parent requirement changes.
- [x] Make match-score return requirements consistent with `REQUIREMENT.md`.
- [x] Confirm the route-surface requirements are consistent with any parent-level persistence decision.
- [x] Add or update traceability links to the revised parent requirements.
- [x] Confirm API validation requirements use the same ranges, formats, and error cases as `REQUIREMENT.md`.

## GUI Requirement Fixes

- [x] Update `GUIREQUIREMENT.md` after parent requirement changes.
- [x] Make match-score display requirements consistent with `REQUIREMENT.md`.
- [x] Confirm simple and advanced workflows match the revised parent definitions.
- [x] Confirm GUI validation requirements use the same ranges, formats, and error cases as `REQUIREMENT.md`.
- [x] Add or update traceability links to the revised parent requirements.

## Review And Verification

- [x] Check that every API requirement traces to a parent requirement.
- [x] Check that every GUI requirement traces to a parent requirement.
- [x] Check that every parent requirement needed by the API and GUI is covered by at least one child requirement.
- [x] Check for conflicting use of domain terms, units, and response semantics.
- [x] Check that every requirement is testable or intentionally marked as a design constraint.
