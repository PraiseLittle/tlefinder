# Phase 19 - Exact Parallel Pass Geometry Execution

> Mandatory rule: Always do the unitary test before writing the code. It is forbidden to change without permission the tests after first coding.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Parallelize exact pass-geometry search across active-satellite records without changing the candidate set, candidate order, filtering behavior, scoring, ranking, result limiting, or public response content.

Approximate candidate budgeting remains disabled for parallel execution in this phase unless explicit tests define equivalent behavior.

## Tasks

- [ ] Write the unit tests for exact parallel pass geometry before implementing it.
  - [ ] Add tests proving parallel and serial geometry search return the same candidates in the same deterministic order.
  - [ ] Add tests proving skipped-record diagnostics are preserved and merged in input-record order.
  - [ ] Add tests proving per-candidate diagnostics are preserved after worker merging.
  - [ ] Add tests proving worker failures are converted to the existing propagation error contract.
  - [ ] Add tests proving one worker, empty records, and very small record sets use the serial path.
  - [ ] Add tests proving approximate candidate budgeting is disabled or rejected when exact parallel mode is requested in this phase.
- [ ] Implement worker-safe input and output objects.
  - [ ] Pass only serializable station, interval, record, and configuration data to workers.
  - [ ] Return candidate geometry, skipped diagnostics, processed counts, and event-search diagnostics from each worker.
  - [ ] Avoid passing `EarthSatellite`, observer, timescale, or `PassAnalysisSession` objects across process boundaries.
  - [ ] Keep worker functions top-level and importable so Windows process spawning works.
- [ ] Implement deterministic chunking.
  - [ ] Split records into stable chunks based on input order.
  - [ ] Preserve each record index through worker execution.
  - [ ] Merge worker results by original record index, not by completion order.
  - [ ] Keep chunk size configurable through the phase 18 configuration model.
- [ ] Run exact pass-geometry work in parallel.
  - [ ] Use the approved backend from phase 18.
  - [ ] Build an isolated `PassAnalysisSession` inside each worker.
  - [ ] Reuse the existing bounded event-search and exact geometry logic inside each worker.
  - [ ] Keep metric computation serial in the parent process for this phase.
  - [ ] Fall back to serial execution for unsupported platforms or unsafe configurations.
- [ ] Merge diagnostics.
  - [ ] Aggregate processed satellite counts from all chunks.
  - [ ] Aggregate skipped-record counts and skipped-record details in deterministic order.
  - [ ] Aggregate event-search span diagnostics across all worker results.
  - [ ] Record worker count, chunk count, backend, and fallback status under `parallel_search`.
  - [ ] Preserve existing `candidate_budget` diagnostics as disabled for exact parallel mode.
- [ ] Verify exact parallel behavior.
  - [ ] Run focused pass-analysis tests.
  - [ ] Run focused engine tests.
  - [ ] Run all core unit tests.
  - [ ] Run the phase 14 benchmark in serial and exact parallel modes against the same cached or fixture dataset.

## Done When

- [ ] Exact parallel pass-geometry search can be enabled explicitly.
- [ ] Exact parallel search returns the same ranked results as serial exact search.
- [ ] Diagnostics make parallel execution visible without changing existing response semantics.
