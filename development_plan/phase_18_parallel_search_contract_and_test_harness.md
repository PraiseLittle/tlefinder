# Phase 18 - Parallel Search Contract and Test Harness

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Define the parallel-search contract before changing the propagation path. This phase must make the intended behavior testable while preserving the current serial search behavior by default.

The first parallel target is active-satellite pass-geometry search across independent TLE records. Ranking, scoring, TLE freshness, and public response semantics must remain controlled by `engine.search_candidates()`.

## Tasks

- [ ] Confirm the parallelization scope before implementation.
  - [ ] Document that satellite pass-geometry propagation is the primary parallel workload.
  - [ ] Keep TLE loading, validation, filtering, scoring, ranking, and result limiting serial in this phase.
  - [ ] Confirm that each worker must build its own Skyfield objects and must not share a `PassAnalysisSession`.
  - [ ] Decide whether phase 18 exposes only an internal core option or a public API option.
  - [ ] Decide the first supported backend: process pool, thread pool, or a small abstraction that can support both.
- [ ] Write the unit tests for the parallel-search contract before implementing it.
  - [ ] Add tests proving serial behavior remains the default.
  - [ ] Add tests proving an explicit parallel option is passed from `engine.search_candidates()` to pass analysis.
  - [ ] Add tests proving invalid worker counts and chunk sizes are rejected with clear errors.
  - [ ] Add tests proving the parallel option is ignored or normalized when only one worker is requested.
  - [ ] Add tests proving diagnostics remain JSON-friendly when parallel settings are present.
- [ ] Define a small parallel configuration model.
  - [ ] Include enabled status, requested worker count, effective worker count, chunk size, backend name, and fallback reason.
  - [ ] Keep default values conservative and deterministic.
  - [ ] Prevent accidental unbounded worker creation.
  - [ ] Make the configuration independent from API schemas until public behavior is approved.
- [ ] Add the pass-analysis execution boundary.
  - [ ] Introduce an internal executor boundary that can run pass geometry serially or in parallel.
  - [ ] Keep the existing `find_candidate_passes()` public signature unchanged.
  - [ ] Keep Skyfield-specific worker code inside `pass_analysis.py` or a closely owned core module.
  - [ ] Preserve the existing session-based metric completion path for serial results.
- [ ] Define diagnostics for parallel search.
  - [ ] Add `parallel_search.enabled`.
  - [ ] Add `parallel_search.backend`.
  - [ ] Add `parallel_search.requested_workers` and `parallel_search.effective_workers`.
  - [ ] Add `parallel_search.chunk_size` and `parallel_search.chunk_count`.
  - [ ] Add `parallel_search.fallback_reason` when execution falls back to serial.
- [ ] Verify phase 18 behavior.
  - [ ] Run focused engine and pass-analysis unit tests.
  - [ ] Run all core unit tests.
  - [ ] Confirm no benchmark or runtime behavior changes unless parallel options are explicitly enabled.

## Done When

- [ ] The codebase has a tested contract for requesting parallel search.
- [ ] Serial search remains the default and produces unchanged results and diagnostics.
- [ ] The next phase can implement real worker execution behind the tested boundary.
