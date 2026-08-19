# Phase 17 - Approximate Budgeted Search

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Add an optional non-parallel budgeted search mode that can stop active-group pass analysis after a shortlist reaches `6 * result_limit`. This phase explicitly trades exactness for latency when the budget policy applies.

Parallel processing is intentionally out of scope for this phase.

## Tasks

- [ ] Confirm the candidate-budget semantics before implementation.
  - [ ] Document that stopping after `6 * result_limit` candidates is approximate because unseen satellites might have scored higher.
  - [ ] Decide whether budgeted search is always enabled or only enabled for active-group/default search.
  - [ ] Decide whether advanced searches with strict filters should disable or raise the budget because they may need more satellites to find enough accepted candidates.
  - [ ] Decide whether callers can request exact mode explicitly.
  - [ ] Decide whether the public diagnostics should expose that a budget was reached.
- [ ] Write the unit tests for candidate budgeting before implementing it.
  - [ ] Add tests proving the default budget is `criteria.result_limit * 6` when budgeted mode applies.
  - [ ] Add tests proving pass analysis stops once the candidate budget is reached.
  - [ ] Add tests proving no stop occurs before the budget is reached.
  - [ ] Add tests proving exact mode still processes every loaded satellite.
  - [ ] Add tests proving diagnostics include candidate budget, budget-reached status, processed satellite count, and unprocessed satellite count.
  - [ ] Add tests proving returned results are still ranked and limited deterministically from the processed shortlist.
- [ ] Add candidate-budget plumbing through the core.
  - [ ] Keep existing public API request fields unchanged for the first increment unless explicit exact/budgeted mode is approved.
  - [ ] Pass an internal candidate budget from `engine.search_candidates()` into pass analysis when budgeted mode applies.
  - [ ] Preserve the existing `find_candidate_passes(records, station, interval)` signature if possible by adding an internal helper for budgeted search.
  - [ ] Keep no-budget behavior available for tests, debugging, and exact-search mode.
- [ ] Stop search work after the approved budget is reached.
  - [ ] Stop propagating additional satellites once the processed shortlist reaches the candidate budget.
  - [ ] Preserve deterministic processing order for the loaded TLE dataset.
  - [ ] Score, threshold, rank, and limit only the processed shortlist.
  - [ ] Do not label budgeted results as exact when the budget was reached.
- [ ] Expose budget diagnostics.
  - [ ] Record whether budgeted mode was enabled.
  - [ ] Record the configured candidate budget.
  - [ ] Record whether the budget was reached.
  - [ ] Record processed and unprocessed satellite counts.
  - [ ] Record processed and returned candidate counts.
- [ ] Verify approximate budgeted behavior.
  - [ ] Confirm budgeted active-group search stops after the configured candidate budget when enough candidates are found.
  - [ ] Confirm exact mode still considers every loaded satellite.
  - [ ] Confirm `result_limit` is still applied after scoring and ranking.
  - [ ] Confirm diagnostics make budgeted and approximate search visible to callers.
  - [ ] Run the phase 14 benchmark and compare runtime against phases 14, 15, and 16.

## Done When

- [ ] The core can run an exact search or an approximate budgeted search according to the approved policy.
- [ ] Budgeted search can stop after `6 * result_limit` candidate passes when the policy applies.
- [ ] Returned candidates remain deterministically scored, ranked, and limited from the processed shortlist.
- [ ] Diagnostics clearly report whether the search was budgeted and whether the budget was reached.
