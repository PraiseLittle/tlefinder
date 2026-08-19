# Phase 16 - Exact Core Search Optimizations

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Reduce active-satellite search runtime without changing the exact candidate set, filtering semantics, scoring, ranking, or result limiting. This phase must preserve exact search behavior.

Parallel processing and approximate candidate budgeting are intentionally out of scope for this phase.

## Tasks

- [ ] Write the unit tests for exact optimization behavior before implementing it.
  - [ ] Add tests proving result content, order, scores, ranks, and diagnostics remain compatible with the current exact search behavior.
  - [ ] Add tests proving geometry-only hard filters can reject candidates before metric computation.
  - [ ] Add tests proving metric-dependent filters still run after the required metrics are available.
  - [ ] Add tests proving returned candidates still include required metrics for API and GUI callers.
  - [ ] Add tests proving no satellite is skipped because of an optimization shortcut.
- [ ] Reuse pass-analysis objects within a search.
  - [ ] Build the ground-station observer once per pass-analysis call instead of once per satellite helper call.
  - [ ] Build each `EarthSatellite` once and reuse it for geometry and metric computation.
  - [ ] Avoid recomputing the same altitude and azimuth values when geometry already computed them.
  - [ ] Keep all Skyfield-specific objects inside `pass_analysis.py`.
- [ ] Apply geometry-first filtering.
  - [ ] Compute candidate geometry before expensive pass metrics.
  - [ ] Apply culmination-altitude and azimuth hard filters after geometry is available.
  - [ ] Preserve rejection diagnostics for geometry-filtered candidates.
  - [ ] Keep filtering behavior identical to the existing exact workflow.
- [ ] Defer metric computation without changing exact results.
  - [ ] Compute Sun proximity only for candidates that survive geometry-only filters and require Sun-proximity filtering, scoring, or response serialization.
  - [ ] Compute satellite-altitude metrics only for candidates that survive geometry-only filters and require altitude filtering or response serialization.
  - [ ] Ensure all returned candidates still contain the same public metric fields as before.
  - [ ] Ensure candidates rejected before metric computation are never returned.
- [ ] Keep scoring and ranking exact.
  - [ ] Score every candidate that survives all hard filters.
  - [ ] Apply thresholding, ranking, and `result_limit` only after all eligible candidates have been considered.
  - [ ] Preserve deterministic ordering and rank assignment.
- [ ] Verify exact optimization behavior.
  - [ ] Confirm pass-analysis, filtering, scoring, ranking, and engine unit tests pass.
  - [ ] Run the phase 14 benchmark and compare runtime against phases 14 and 15.
  - [ ] Confirm diagnostics distinguish exact optimizations from approximate budgeted search.

## Done When

- [ ] Active-group search is faster while still considering every satellite in the loaded dataset.
- [ ] Observer, satellite, and repeated geometry computations are reduced without moving orbital logic outside `pass_analysis.py`.
- [ ] Geometry-first filtering and deferred metrics do not change returned results.
- [ ] The engine still produces exact ranked results before any approximate budget phase begins.
