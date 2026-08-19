# Phase 15 - Bounded Pass Event Search

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Reduce the amount of Skyfield event searching performed for each satellite by replacing the current day-wide event span with a bounded lookaround around the requested search window.

Parallel processing is intentionally out of scope for this phase.

## Tasks

- [ ] Write the unit tests for bounded event-search behavior before implementing it.
  - [ ] Add tests proving `_event_search_interval()` no longer starts at midnight and scans roughly two full days for ordinary search windows.
  - [ ] Add tests proving the event-search span includes the requested search window.
  - [ ] Add tests proving the event-search span includes a lookback before the search-window start so ongoing passes can still be detected.
  - [ ] Add tests proving the event-search span includes a lookahead after the search-window end so real set events can still be found.
  - [ ] Preserve tests for partial-window passes, overlap-only windows, midnight overlap, and previous-day rise behavior.
- [ ] Define the bounded lookaround policy.
  - [ ] Add a named multiplier constant, initially `6 * search_window_duration`.
  - [ ] Add a small minimum lookaround duration so very short windows still detect realistic in-progress passes.
  - [ ] Add a maximum lookaround duration if needed to prevent accidental multi-day event searches.
  - [ ] Keep the policy internal to `pass_analysis.py` unless a later product decision makes it user-configurable.
- [ ] Implement bounded event-search intervals.
  - [ ] Replace the current midnight-to-two-days interval for the primary event search.
  - [ ] Keep the fallback search only for cases where it is still required by partial-pass correctness.
  - [ ] Prefer bounded fallback spans over previous full-day fallback spans.
  - [ ] Preserve UTC-aware datetime handling and existing propagation error behavior.
- [ ] Add event-search diagnostics.
  - [ ] Record the event-search start and end timestamps used for each detected or skipped satellite where practical.
  - [ ] Record whether fallback event search was used.
  - [ ] Record whether the candidate was partial because the pass extended beyond the requested search window.
- [ ] Verify result compatibility.
  - [ ] Confirm existing pass-analysis unit tests still pass.
  - [ ] Confirm engine tests still pass.
  - [ ] Run the phase 14 benchmark and compare active-group pass-analysis runtime against the baseline.

## Done When

- [ ] Pass analysis no longer performs a multi-day event search for ordinary active-group searches.
- [ ] Partial-window and overlap-only passes remain supported.
- [ ] Active-group search is measurably faster without changing expected fixture results.
