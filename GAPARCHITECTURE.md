# Core Architecture Gaps

This file records known gaps to address in the core architecture document after the requirement updates.

## 1. Validation Rules

`ARCHITECTURE.md` should make the validation contract as explicit as `REQUIREMENT.md`.

Required validation details to add:

- latitude must be numeric and within `[-90, 90]` degrees
- longitude must be numeric and within `[-180, 180]` degrees
- elevation must be numeric, in meters above mean sea level, and within `[-500, 8000] m`
- search-window duration must be greater than `0` minutes and no greater than `30` minutes
- culmination apparent-altitude bounds must be within `[0, 90]` degrees
- azimuth values must be numeric and within `[0, 360)` degrees
- Sun-proximity values must be numeric and within `[0, 180]` degrees
- satellite-altitude values must be numeric, in kilometers, and within `[200, 15000] km`
- range constraints must reject `minimum > maximum`
- requested result count must be a strictly positive integer
- candidate-selection threshold must be numeric and within `[0, 100]`

## 2. Time Handling

The core architecture must consistently require unambiguous search-window start times:

- accepted core values are UTC datetimes or local datetimes with an explicit UTC offset
- timezone names are not part of the accepted core input contract
- the core must reject naive datetimes
- the core must never infer a UTC offset from the optical ground station
- GUI and API layers may provide controls or parsing helpers, but they must construct a timezone-aware `SearchWindow.start_at` with an explicit UTC offset before calling the core

## 3. Out Of Scope For This Gap File

TLE freshness is intentionally aligned with the current architecture: freshness is enforced by the TLE repository workflow and failure stops the search with an explicit error.

Pass-detection details remain open for separate analysis.
