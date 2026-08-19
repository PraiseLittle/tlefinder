# Phase 7 - Core Default Scoring and Satellite Group Gap Closure

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Close the two core gaps recorded in `GAPARCHITECTURE_SIMPLE_SEARCH.md` by making the core-owned default scoring behavior explicit, testable, and deterministic, and by enforcing satellite-group validation and dataset selection before propagation.

## Tasks

- [ ] Write the unit tests for default pass-duration and pass-timing scoring before implementing it.
  - [ ] Add tests proving candidate-pass duration is derived from `CandidatePass.geometry.end_time_utc - CandidatePass.geometry.start_time_utc`.
  - [ ] Add tests proving a longer candidate pass receives a higher duration score than an otherwise equivalent shorter pass.
  - [ ] Add tests proving duration scoring returns normalized values on the `0..100` scale.
  - [ ] Add tests proving pass timing uses the observable start inside the search window: `max(candidate.geometry.start_time_utc, search_window_start_utc)`.
  - [ ] Add tests proving a candidate that is already observable at the search-window start scores as earlier than a candidate that begins later in the window.
  - [ ] Add tests proving pass-timing scoring returns normalized values on the `0..100` scale.
  - [ ] Add tests covering boundary behavior at the search-window start, near the search-window end, and for partial-window passes.
  - [ ] Add tests proving equal duration and equal observable timing produce equal component scores.
- [ ] Write the unit tests for default match-score composition before implementing it.
  - [ ] Add tests proving a request with simple-search default criteria no longer gives every candidate a neutral `100` score.
  - [ ] Add tests proving default scoring combines pass-duration and pass-timing components deterministically.
  - [ ] Add tests proving pass-duration and pass-timing both influence the final score for a default request.
  - [ ] Add tests proving disabled optional filtering criteria still do not add hidden scoring weight.
  - [ ] Add tests proving explicitly enabled culmination, azimuth, and Sun-proximity preferences continue to contribute only through documented scoring components.
  - [ ] Add tests proving the official score is independent of GUI/API workflow labels such as simple search or full search.
  - [ ] Add engine tests proving the normalized search-window context is passed into scoring after validation and UTC normalization.
- [ ] Define the core-owned representation of default scoring behavior.
  - [ ] Decide whether the default behavior is represented by a `SearchCriteria` field, a small core scoring profile enum, or a documented always-on core scoring policy.
  - [ ] Keep the chosen representation independent from simple-search and full-search mode labels.
  - [ ] Keep scoring configuration out of GUI/API request ownership; adapters may select only the supported core default behavior required by the shared request contract.
  - [ ] Document which scoring components are always applicable and which components only apply when matching criteria are explicitly enabled.
  - [ ] Preserve backward-compatible dataclass defaults where possible so existing core callers still construct valid `SearchCriteria` objects.
- [ ] Implement the default scoring inputs in `scoring.py`.
  - [ ] Add `score_pass_duration_fit(candidate: CandidatePass, criteria: SearchCriteria) -> float`, or the final approved equivalent signature.
  - [ ] Add `score_pass_timing_fit(candidate: CandidatePass, criteria: SearchCriteria, window: SearchWindow) -> float`, or an equivalent signature that receives normalized UTC search-window context.
  - [ ] Compute pass duration from `PassGeometry` instead of storing duplicate duration in `PassMetrics`.
  - [ ] Compute observable pass start from `max(candidate.geometry.start_time_utc, search_window_start_utc)`.
  - [ ] Keep duration and timing scoring deterministic and free of adapter-specific defaults.
  - [ ] Export the new public scoring helpers from `scoring.py`.
- [ ] Update score orchestration in `engine.py`.
  - [ ] Pass the normalized search-window context from `time_utils.build_search_interval()` into scoring.
  - [ ] Keep validation before interval construction, TLE loading, propagation, filtering, scoring, thresholding, ranking, and limiting.
  - [ ] Confirm `find_best_candidate()` and `find_next_candidate()` continue to use the same scoring path as `search_candidates()`.
  - [ ] Preserve `NO_RESULT` as a normal response state when duration/timing scoring plus thresholding removes all candidates.
- [ ] Write the unit tests for satellite-group validation before implementing any changes.
  - [ ] Add tests proving `validate_search_request()` accepts `SatelliteGroup.ACTIVE`, `SatelliteGroup.VISUAL`, and `SatelliteGroup.AMATEUR`.
  - [ ] Add tests proving raw strings such as `"active"`, unsupported enum-like objects, and `None` are rejected as invalid `SearchRequest.satellite_group` values.
  - [ ] Add tests proving invalid satellite groups fail before TLE loading or propagation starts.
  - [ ] Add engine tests proving the requested satellite group is passed unchanged to `tle_repository.load_tle_dataset()`.
  - [ ] Add repository tests proving each supported group resolves to its configured TLE source before records are parsed or propagated.
- [ ] Implement or tighten satellite-group validation and dataset selection.
  - [ ] Keep `SearchRequest.satellite_group` typed as `SatelliteGroup`.
  - [ ] Ensure validation rejects anything outside `ACTIVE`, `VISUAL`, and `AMATEUR` with deterministic `ValidationError` messages.
  - [ ] Keep TLE loading responsible for selecting the requested source group before propagation.
  - [ ] Ensure parsed `TleRecord.source_group` and `SatelliteRecord.metadata["source_group"]` match the requested group.
  - [ ] Avoid adding satellite-group branching to pass analysis, filtering, scoring, or ranking.
- [ ] Update the architecture documentation after the core behavior is covered by tests.
  - [ ] Update `ARCHITECTURE.md` so `SearchCriteria` or the approved core scoring mechanism explicitly represents default scoring behavior.
  - [ ] Document that default scoring considers pass duration and observable pass timing without receiving simple-search or full-search labels.
  - [ ] Document that candidate-pass duration is derived from `PassGeometry.end_time_utc - PassGeometry.start_time_utc`.
  - [ ] Document that duration is not duplicated in `PassMetrics` unless implementation evidence later proves recomputation is a problem.
  - [ ] Document that observable pass timing is computed as `max(pass_start_time_utc, search_window.start_at_utc)`.
  - [ ] Add `score_pass_duration_fit()` and `score_pass_timing_fit()` to the `scoring.py` responsibility section with their final signatures.
  - [ ] Document that both new scoring components return normalized values on the `0..100` scale.
  - [ ] Add validation documentation that `SearchRequest.satellite_group` must be one of `ACTIVE`, `VISUAL`, or `AMATEUR`.
  - [ ] Document that TLE loading selects the requested satellite group before propagation.
- [ ] Run the focused and full core test suites.
  - [ ] Run the scoring unit tests first.
  - [ ] Run the validation and TLE repository unit tests next.
  - [ ] Run the engine orchestration tests after the scoring signature is updated.
  - [ ] Run all `tlefinder/tests/unit` tests after the gap fixes.
  - [ ] Confirm the core package still imports without GUI, API, Flask, or template dependencies.

## Done When

- [ ] `ARCHITECTURE.md` states the default scoring behavior and satellite-group validation rules listed in `GAPARCHITECTURE_SIMPLE_SEARCH.md`.
- [ ] `scoring.py` exposes deterministic pass-duration and pass-timing scoring helpers on the `0..100` scale.
- [ ] `compute_match_score()` uses the documented default scoring behavior without workflow labels.
- [ ] Candidate-pass duration is derived from `PassGeometry` and is not duplicated in `PassMetrics`.
- [ ] Pass-timing scoring uses the observable start inside the normalized search window.
- [ ] `validate_search_request()` rejects unsupported satellite groups before TLE loading or propagation.
- [ ] TLE loading selects the requested `SatelliteGroup` before candidate propagation.
- [ ] The full core unit suite passes with the default scoring and satellite-group gap fixes.
