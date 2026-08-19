# Core Architecture Gaps: Scoring and Satellite Groups

This file records core architecture gaps introduced by the updated requirements for scoring behavior and satellite-group selection.

## 1. Default Scoring Behavior Is Not Yet Represented In The Core Model

`REQUIREMENT.md` now requires the default scoring behavior to consider:

- candidate-pass duration, where longer passes score better
- pass timing, where passes observable sooner from the search-window start score better

`ARCHITECTURE.md` does not define how the shared core `SearchRequest` or `SearchCriteria` represents this default scoring behavior.

Required architecture update:

- define how the core default scoring behavior considers pass duration and pass timing
- define whether the default scoring behavior is represented by a core scoring profile, explicit core criteria fields, or another core-owned mechanism
- preserve the rule that the core does not receive or branch on workflow labels such as simple-search or full-search mode

## 2. Pass Duration And Timing Inputs Need Explicit Core Data Ownership

`ARCHITECTURE.md` currently defines `PassGeometry` with pass start/end times and `PassMetrics` with satellite altitude and Sun proximity, but it does not explicitly state that candidate-pass duration is derived from pass start/end times or where observable start timing is computed.

Required architecture update:

- explicitly state that candidate-pass duration is derived from `PassGeometry.end_time_utc - PassGeometry.start_time_utc`
- avoid storing duplicate duration in `PassMetrics` unless later implementation evidence shows repeated recomputation is a real problem
- define the pass-timing scoring input as the observable start within the search window: `max(pass_start_time_utc, search_window.start_at_utc)`
- specify where this value is computed so scoring remains deterministic and testable

## 3. `scoring.py` Needs New Public Responsibilities

`ARCHITECTURE.md` currently lists scoring functions for culmination, azimuth, and Sun proximity only.

Required architecture update:

- add `score_pass_duration_fit(candidate: CandidatePass, criteria: SearchCriteria) -> float`
- add `score_pass_timing_fit(candidate: CandidatePass, criteria: SearchCriteria, window: SearchWindow) -> float`, or an equivalent signature that gives scoring access to the normalized search-window start
- document that both scoring components return normalized values on the `0..100` scale
- document that the default scoring behavior considers these two components

## 4. Satellite Group Validation Is Underspecified

`ARCHITECTURE.md` already has `SatelliteGroup` and lists `ACTIVE`, `VISUAL`, and `AMATEUR`, but the validation section does not explicitly require satellite-group validation.

Required architecture update:

- add validation that `SearchRequest.satellite_group` must be one of `ACTIVE`, `VISUAL`, or `AMATEUR`
- keep TLE loading responsible for selecting the requested group before propagation
