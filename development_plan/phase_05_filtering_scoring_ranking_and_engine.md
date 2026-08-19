# Phase 5 - Filtering, Scoring, Ranking, and Engine

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Finish the reusable core search engine by applying hard filters, computing deterministic scores, ranking results, and orchestrating the full workflow from one entrypoint.

## Tasks

- [ ] Write the unit tests for filtering, scoring, ranking, and orchestration before implementing them.
  - [ ] Add tests for hard acceptance and rejection for each enabled criterion.
  - [ ] Add tests for azimuth wrap-around semantics such as `350 +/- 20`.
  - [ ] Add tests for deterministic score calculation on the `0..100` scale.
  - [ ] Add tests for thresholding, stable ordering on ties, and result limiting.
  - [ ] Add engine tests with mocked repository and pass-analysis dependencies.
- [ ] Implement `filtering.py`.
  - [ ] Add culmination, azimuth, Sun-proximity, and satellite-altitude matching helpers for the first core increment.
  - [ ] Do not add magnitude or object-type filtering in this phase because those criteria are deferred beyond the frozen core increment.
  - [ ] Keep filtering limited to hard constraints only.
  - [ ] Record rejection reasons in diagnostics where useful.
- [ ] Implement `scoring.py`.
  - [ ] Add deterministic soft-preference scoring on the `0..100` scale.
  - [ ] Use equal weights across enabled criteria in the first implementation increment unless a new scoring specification is approved.
  - [ ] Ensure disabled criteria contribute no hidden weight.
- [ ] Implement `ranking.py`.
  - [ ] Add score-threshold application.
  - [ ] Add stable sorting with documented secondary keys.
  - [ ] Add result limiting and rank assignment.
- [ ] Implement `engine.py`.
  - [ ] Add `search_candidates()` as the single orchestration entrypoint.
  - [ ] Add `find_best_candidate()` as a convenience wrapper.
  - [ ] Return `RESULTS` or `NO_RESULT` as response states and reserve exceptions for true failure cases.
- [ ] Freeze the internal core contract before adapter work starts.
  - [ ] Confirm the engine can run end-to-end without Flask, forms, or templates.
  - [ ] Confirm the response model contains everything required by GUI, API, and Python callers.
  - [ ] Confirm `PassMetrics.magnitude | None` exists as reserved future shape but is not actively computed, filtered, or scored.
  - [ ] Confirm magnitude and object-type stay explicitly out of active criteria and active scoring/filtering for this increment.
  - [ ] Confirm core modules import only the new `tlefinder` modules and declared third-party dependencies.

## Done When

- [ ] The core search engine runs end-to-end from `SearchRequest` to `SearchResponse`.
- [ ] The ranking outcome is deterministic for the same request and dataset.
- [ ] `NO_RESULT` is returned as a normal response state rather than an exception.
