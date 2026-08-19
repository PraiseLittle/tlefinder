# Phase 14 - Core Search Performance Baseline and Diagnostics

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Make the active-satellite search performance problem measurable before changing the propagation behavior. This phase must not change search results, ranking, or satellite-selection semantics.

Parallel processing is intentionally out of scope for this optimization sequence.

## Tasks

- [x] Write the unit tests for performance diagnostics before implementing them.
  - [x] Add engine tests proving existing count diagnostics are preserved.
  - [x] Add tests for new timing diagnostics using a deterministic fake clock or injectable timer.
  - [x] Add tests proving diagnostics stay JSON-friendly for API and GUI adapters.
  - [x] Add tests proving no timing diagnostic changes the returned candidate ordering.
- [x] Add lightweight timing diagnostics around the core search stages.
  - [x] Measure validation and interval normalization.
  - [x] Measure TLE dataset loading.
  - [x] Measure pass analysis.
  - [x] Measure filtering, scoring, thresholding, ranking, and limiting.
  - [x] Keep timings best-effort diagnostics only; do not use them for control flow.
- [x] Add pass-analysis work diagnostics.
  - [x] Record the number of satellite records inspected.
  - [x] Record the number of candidate geometries found.
  - [x] Record the number of skipped records where diagnostics are available.
  - [x] Record the event-search span used by pass analysis once phase 15 introduces a bounded span.
- [x] Add a repeatable local benchmark command or script.
  - [x] Benchmark `active`, `visual`, and `amateur` groups separately when fixture or cached data is available.
  - [x] Include at least one default/simple search and one advanced search with geometry filters.
  - [x] Print total runtime, pass-analysis runtime, satellite count, candidate count, filtered count, and returned count.
  - [x] Keep the benchmark outside the normal unit-test suite unless it is fast and deterministic.
- [x] Capture the baseline before behavior changes.
  - [x] Record the active-group baseline with the current implementation.
  - [x] Record the requested window duration, station, TLE source group, result limit, and cache state used for the measurement.
  - [x] Add the baseline numbers to the phase notes or a small benchmark results document.

## Done When

- [x] The current search path reports stable count and timing diagnostics.
- [x] The added diagnostics do not change result content, order, status, or exceptions.
- [x] There is a repeatable way to measure active-group search time before and after later optimization phases.
