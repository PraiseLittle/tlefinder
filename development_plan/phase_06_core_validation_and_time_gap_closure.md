# Phase 6 - Core Validation and Time Gap Closure

> Mandatory rule: Always do the unit tests before writing the code. It is forbidden to change the tests after the first coding step without permission.

> Environment rule: Use the Python version selected by the global `pyenv` configuration. Manage dependencies and commands with Poetry.

## Goal

Close the two core gaps recorded in `GAPARCHITECTURE.md` by making the validation contract and time-handling contract explicit, tested, and enforced consistently in the reusable core package.

## Tasks

- [ ] Write the unit tests for the stricter core validation contract before implementing it.
  - [ ] Add tests proving latitude must be numeric, finite, and within `[-90, 90]` degrees.
  - [ ] Add tests proving longitude must be numeric, finite, and within `[-180, 180]` degrees.
  - [ ] Add tests proving elevation must be numeric, finite, expressed in meters above mean sea level, and within `[-500, 8000] m`.
  - [ ] Add tests proving search-window duration must be numeric, finite, greater than `0` minutes, and no greater than `30` minutes.
  - [ ] Add tests proving culmination apparent-altitude bounds must be numeric, finite, and within `[0, 90]` degrees.
  - [ ] Add tests proving azimuth targets must be numeric, finite, and within `[0, 360)` degrees.
  - [ ] Add tests proving Sun-proximity bounds must be numeric, finite, and within `[0, 180]` degrees.
  - [ ] Add tests proving satellite-altitude bounds must be numeric, finite, expressed in kilometers, and within `[200, 15000] km`.
  - [ ] Add tests proving every range constraint rejects `minimum > maximum`.
  - [ ] Add tests proving requested result count is a strictly positive integer and rejects booleans, floats, and strings.
  - [ ] Add tests proving candidate-selection threshold must be numeric, finite, and within `[0, 100]`.
- [ ] Implement the stricter validation rules in `validation.py`.
  - [ ] Replace the current ground-station elevation upper bound with the requirement range of `[-500, 8000] m`.
  - [ ] Keep numeric validation centralized so booleans, non-real values, `NaN`, and infinities fail consistently.
  - [ ] Add explicit satellite-altitude lower and upper constants for `200 km` and `15000 km`.
  - [ ] Apply the satellite-altitude constants to both minimum and maximum range bounds.
  - [ ] Keep culmination, Sun-proximity, range-consistency, result-limit, and threshold validation deterministic and message-oriented for adapters.
  - [ ] Confirm disabled optional criteria remain valid when set to `None`.
- [ ] Write the unit tests for unambiguous core time handling before implementing it.
  - [ ] Add tests accepting UTC datetimes whose timezone is `datetime.timezone.utc`.
  - [ ] Add tests accepting local datetimes whose timezone is an explicit fixed UTC offset, such as `datetime.timezone(timedelta(hours=1))`.
  - [ ] Add tests rejecting naive datetimes in `validate_search_window()`.
  - [ ] Add tests rejecting timezone-name datetimes, including `zoneinfo.ZoneInfo("Europe/Paris")`, even though Python can compute an offset from them.
  - [ ] Add tests proving equivalent UTC and fixed-offset local inputs normalize to the same UTC interval.
  - [ ] Add tests proving no validation or normalization path reads the optical ground station to infer a UTC offset.
- [ ] Implement the stricter time contract in `validation.py` and `time_utils.py`.
  - [ ] Treat the core contract as accepting only UTC or fixed-offset aware datetimes.
  - [ ] Reject timezone-name `tzinfo` implementations at the core boundary instead of normalizing them.
  - [ ] Keep `normalize_start_time_to_utc()` focused on conversion after the contract has been validated.
  - [ ] Decide whether `time_utils.py` should raise `ValidationError` or preserve a narrow defensive `ValueError`, then document the chosen behavior in tests.
  - [ ] Ensure `build_search_interval()` returns timezone-aware UTC start and end datetimes without using station data.
- [ ] Update the architecture documentation after the core behavior is covered by tests.
  - [ ] Expand the `ARCHITECTURE.md` validation section so each required rule from `GAPARCHITECTURE.md` is explicit.
  - [ ] Update the `ARCHITECTURE.md` time-handling section to state that timezone names are not accepted by the core contract.
  - [ ] Document that GUI and API adapters may parse richer user inputs, but must pass a timezone-aware `SearchWindow.start_at` with an explicit UTC offset to the core.
  - [ ] Keep TLE freshness and pass-detection details out of this phase because `GAPARCHITECTURE.md` marks them out of scope.
- [ ] Run the core test suite and inspect regressions.
  - [ ] Run the validation and time utility unit tests first.
  - [ ] Run all `tlefinder/tests/unit` tests after the gap fixes.
  - [ ] Update any test fixtures that currently use timezone-name `ZoneInfo` objects so they use explicit fixed offsets instead.
  - [ ] Confirm the core package still imports without GUI, API, Flask, or template dependencies.

## Done When

- [ ] `ARCHITECTURE.md` states every validation and time-handling rule listed in `GAPARCHITECTURE.md`.
- [ ] `validate_search_request()` rejects every invalid value described by the gap file with deterministic `ValidationError` messages.
- [ ] The core accepts UTC and fixed-offset local datetimes, rejects naive and timezone-name datetimes, and normalizes accepted start times to UTC.
- [ ] The full core unit suite passes with the stricter validation and time contract.
