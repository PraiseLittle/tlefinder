# Phase 21 - Parallel Search Benchmarking, Tuning, and Release

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Choose safe parallel-search defaults from measured results, harden operational behavior, and document how OGS users should select exact or approximate search modes.

This phase turns the parallel implementation into a predictable operational feature instead of a local experiment.

## Tasks

- [ ] Write the unit tests for benchmark and configuration behavior before implementing it.
  - [ ] Add tests proving benchmark CLI options parse worker count, chunk size, backend, and exact or budgeted mode.
  - [ ] Add tests proving unsafe worker counts are clamped or rejected consistently.
  - [ ] Add tests proving default parallel settings can be derived without live network access.
  - [ ] Add tests proving benchmark output includes enough data to compare serial and parallel runs.
  - [ ] Add tests proving diagnostics remain JSON-friendly after tuning fields are added.
- [ ] Extend the benchmark tooling.
  - [ ] Add benchmark options for serial exact, parallel exact, and parallel budgeted search.
  - [ ] Add options for worker count and chunk size.
  - [ ] Print total runtime, pass-analysis runtime, scheduling runtime, satellite count, processed count, candidate count, returned count, and approximate status.
  - [ ] Support cached active-group datasets large enough to represent real operational search.
  - [ ] Keep benchmark commands outside the normal unit-test suite.
- [ ] Measure realistic active-satellite workloads.
  - [ ] Benchmark a small fixture dataset to confirm correctness overhead.
  - [ ] Benchmark a cached full active dataset with exact serial mode.
  - [ ] Benchmark the same cached full active dataset with exact parallel mode across several worker counts.
  - [ ] Benchmark approximate parallel mode for broad default searches.
  - [ ] Record CPU count, Python version, OS, cache state, TLE source age, search window, station, and result limit.
- [ ] Tune default policy.
  - [ ] Choose whether parallel search should be automatic for active-group searches.
  - [ ] Choose default worker count based on measured speedup and Windows process-spawn overhead.
  - [ ] Choose default chunk size based on throughput and cancellation responsiveness.
  - [ ] Preserve a clear exact mode for operational cases where approximate results are not acceptable.
  - [ ] Keep defaults conservative if the benchmark does not show consistent speedup.
- [ ] Harden operational behavior.
  - [ ] Ensure process pools are closed promptly after each search.
  - [ ] Ensure cancellations and worker failures do not leave hanging child processes.
  - [ ] Ensure logs and diagnostics do not include excessive per-satellite data for large active datasets.
  - [ ] Ensure parallel execution works from CLI, API server, and packaged entry points.
  - [ ] Confirm Windows spawn behavior is covered by tests or manual verification notes.
- [ ] Update documentation.
  - [ ] Document exact serial, exact parallel, and approximate parallel modes.
  - [ ] Document the TLE freshness assumptions for OGS tracking searches.
  - [ ] Document when strict filters or small datasets fall back to serial or exact behavior.
  - [ ] Add benchmark results to the existing benchmark notes or a new phase 21 benchmark document.
  - [ ] Document recommended settings for local development and operational deployment.
- [ ] Final verification.
  - [ ] Run all unit tests.
  - [ ] Run selected API functional tests if public API behavior changed.
  - [ ] Run GUI type checks and build if GUI behavior changed.
  - [ ] Run benchmark comparisons and record the final numbers.
  - [ ] Confirm the feature can be disabled quickly if operational issues are found.

## Done When

- [ ] Parallel search defaults are chosen from recorded benchmark evidence.
- [ ] OGS users can understand when search results are exact and when they are approximate.
- [ ] The release path includes tests, diagnostics, documentation, and a rollback option.
