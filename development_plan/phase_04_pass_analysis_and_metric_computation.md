# Phase 4 - Pass Analysis and Metric Computation

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Implement the Skyfield-based propagation layer that detects candidate passes and computes the pass geometry and metrics required by filtering and scoring.

## Tasks

- [ ] Write the unit tests for pass analysis before implementing it.
  - [ ] Add tests for altitude and azimuth computation at a known instant.
  - [ ] Add tests for pass detection inside a bounded search interval.
  - [ ] Add tests for partial-window passes where the pass end must be estimated or clipped.
  - [ ] Add tests for mean satellite altitude and Sun-proximity computation.
  - [ ] Add tests proving deterministic results for the same TLE fixture and search interval.
- [ ] Implement the Skyfield location and propagation helpers.
  - [ ] Convert `GroundStation` into the observer location used by Skyfield.
  - [ ] Add `compute_alt_az()` and `compute_satellite_altitude_km()`.
  - [ ] Keep third-party orbital logic isolated inside `pass_analysis.py`.
- [ ] Implement pass detection and geometry extraction.
  - [ ] Add `compute_pass_geometry()` for rise, culmination, and set event extraction.
  - [ ] Add support for partially visible passes inside the requested search window.
  - [ ] Preserve UTC timestamps consistently in the returned geometry.
- [ ] Implement pass-level metric computation.
  - [ ] Add `compute_pass_metrics()` and populate `PassMetrics`.
  - [ ] Add `compute_sun_proximity()` as a first-class metric rather than a presentation detail.
  - [ ] Reserve `PassMetrics.magnitude | None` in this phase so the core contract matches the architecture.
  - [ ] Do not compute magnitude in this phase; leave the reserved field unset until a later dedicated increment.
- [ ] Implement the candidate-pass aggregation flow.
  - [ ] Add `find_candidate_passes()` over a list of `SatelliteRecord` objects.
  - [ ] Attach per-candidate diagnostics for partial data, skipped events, or propagation anomalies.
  - [ ] Raise typed propagation errors when the workflow cannot continue safely.

## Done When

- [ ] The core can produce `CandidatePass` objects from fixture TLE data and a validated request interval.
- [ ] Pass geometry and pass metrics are generated deterministically for repeatable test data.
- [ ] Propagation logic is isolated from filtering, scoring, and presentation code.
