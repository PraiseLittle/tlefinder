# Phase 20 - Budgeted Parallel Search and API Plumbing

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Support low-latency active-satellite search by combining parallel pass-geometry execution with the approved approximate candidate-budget policy. Expose the behavior through the appropriate core, API, and GUI boundaries only after the unit contract is fixed.

This phase explicitly allows approximate behavior when budgeted mode is enabled and diagnostics report that unseen satellites may exist.

## Tasks

- [ ] Confirm the product-facing parallel policy before implementation.
  - [ ] Decide whether parallel search is opt-in, automatic for the active group, or controlled by server configuration.
  - [ ] Decide whether API callers can request exact serial, exact parallel, and approximate parallel modes.
  - [ ] Decide whether the GUI exposes a mode toggle or relies on API defaults.
  - [ ] Decide default worker count and chunk size for Windows development and deployment.
  - [ ] Document when strict filters disable approximate budgeting.
- [ ] Write the unit tests for budgeted parallel search before implementing it.
  - [ ] Add tests proving budgeted parallel mode processes chunks in deterministic waves.
  - [ ] Add tests proving candidate budget checks happen after deterministic merge points, not by worker completion order.
  - [ ] Add tests proving unprocessed satellite counts include chunks that were never started after the budget was reached.
  - [ ] Add tests proving results are marked approximate when the budget is reached.
  - [ ] Add tests proving exact parallel mode still processes every satellite.
  - [ ] Add tests proving strict-filter searches disable approximate budgeting even when parallel execution is enabled.
- [ ] Implement budget-aware parallel scheduling.
  - [ ] Submit work in bounded waves instead of submitting the full active dataset at once.
  - [ ] Merge completed wave results in input-record order before checking the candidate budget.
  - [ ] Stop scheduling new waves once the approved budget has been reached.
  - [ ] Allow already-running chunks to finish and report their processed counts.
  - [ ] Keep deterministic result ordering from the processed shortlist.
- [ ] Integrate parallel options into the core engine.
  - [ ] Add explicit core kwargs or a configuration object for parallel search.
  - [ ] Keep default exact serial behavior available for tests and debugging.
  - [ ] Combine `candidate_budget` diagnostics with `parallel_search` diagnostics.
  - [ ] Preserve existing timing diagnostics and add a separate parallel scheduling timing when useful.
- [ ] Add API and GUI plumbing only after core behavior is tested.
  - [ ] Extend API schemas if public caller control is approved.
  - [ ] Add route tests proving request options map to core kwargs correctly.
  - [ ] Add adapter tests proving parallel and budget diagnostics serialize unchanged.
  - [ ] Update GUI client types if the API response schema changes.
  - [ ] Keep UI controls minimal and avoid exposing unsafe worker counts directly to ordinary users.
- [ ] Verify budgeted parallel behavior.
  - [ ] Run focused core unit tests.
  - [ ] Run focused API unit tests if API plumbing is included.
  - [ ] Run GUI type checks if GUI response types change.
  - [ ] Run the phase 14 benchmark in serial exact, parallel exact, and parallel budgeted modes.

## Done When

- [ ] Active-group search can use parallel workers and candidate budgeting together according to the approved policy.
- [ ] Approximate results are clearly labeled when the budget is reached.
- [ ] API and GUI boundaries expose only approved controls and preserve JSON-friendly diagnostics.
