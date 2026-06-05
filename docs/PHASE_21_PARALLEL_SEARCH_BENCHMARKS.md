# Phase 21 Parallel Search Benchmark And Operating Notes

Captured on 2026-05-26 with `poetry run` using Python 3.10.11.

Environment:

- CPU count: `12`
- OS: `Windows-10-10.0.26200-SP0`
- Python executable: `.venv\Scripts\python.exe`
- Station: latitude `48.8566`, longitude `2.3522`, elevation `35 m`
- Backend: `process_pool`
- Default API policy: parallel search disabled unless `TLEFINDER_PARALLEL_SEARCH_ENABLED=true`
- Default enabled shape: `4` workers, chunk size `32`

## Search Modes

Exact serial mode is selected by omitting both `parallel_search` and
`approximate_budgeted`. It processes every loaded TLE record in deterministic
source order and returns exact ranked results.

Exact parallel mode is selected by passing a `ParallelSearchConfig` and leaving
`approximate_budgeted=False`. It still processes every loaded TLE record, but
pass-geometry work is split into process-pool chunks. Results are merged in
input-record order before filtering, scoring, ranking, and limiting.

Approximate parallel mode is selected by passing both `parallel_search` and
`approximate_budgeted=True`. It applies only to `ACTIVE` searches without strict
hard filters. The candidate budget is `result_limit * 6`; once the budget is
reached, later records are not searched. Diagnostics mark the result
approximate because unseen satellites might have produced higher scores.

Strict hard filters, non-`ACTIVE` groups, single-worker requests, empty record
sets, and small datasets that fit in one chunk fall back to exact or serial
behavior. API clients do not pass raw worker controls; deployment settings own
that policy.

## Benchmark Commands

Fixture correctness and overhead checks:

```powershell
poetry run tlefinder-benchmark-core --groups active --cases simple,advanced --start-at 2026-05-12T14:50:00Z --duration-minutes 12 --execution-mode serial_exact
poetry run tlefinder-benchmark-core --groups active --cases simple,advanced --start-at 2026-05-12T14:50:00Z --duration-minutes 12 --execution-mode parallel_exact --parallel-workers 2 --parallel-chunk-size 1
poetry run tlefinder-benchmark-core --groups active --cases simple,advanced --start-at 2026-05-12T14:50:00Z --duration-minutes 12 --execution-mode parallel_budgeted --parallel-workers 2 --parallel-chunk-size 1
```

Full active cache checks:

```powershell
poetry run tlefinder-benchmark-core --source cache --cache-dir tmp_tle_cache --groups active --cases simple --start-at 2026-05-26T20:00:00Z --duration-minutes 10 --max-tle-age-hours 72 --execution-mode serial_exact
poetry run tlefinder-benchmark-core --source cache --cache-dir tmp_tle_cache --groups active --cases simple --start-at 2026-05-26T20:00:00Z --duration-minutes 10 --max-tle-age-hours 72 --execution-mode parallel_exact --parallel-workers 2 --parallel-chunk-size 32
poetry run tlefinder-benchmark-core --source cache --cache-dir tmp_tle_cache --groups active --cases simple --start-at 2026-05-26T20:00:00Z --duration-minutes 10 --max-tle-age-hours 72 --execution-mode parallel_exact --parallel-workers 4 --parallel-chunk-size 32
poetry run tlefinder-benchmark-core --source cache --cache-dir tmp_tle_cache --groups active --cases simple --start-at 2026-05-26T20:00:00Z --duration-minutes 10 --max-tle-age-hours 72 --execution-mode parallel_budgeted --parallel-workers 4 --parallel-chunk-size 32
```

The benchmark command is a development script and is not part of the normal
unit-test suite.

## Fixture Results

Fixture cache state: deterministic `tests/fixtures/active_sample.tle`, `2`
records, search window `2026-05-12T14:50:00Z` for `12` minutes, result limit
`10`, TLE source age `2.833 h`.

| mode | workers | chunk | case | total_ms | pass_ms | satellites | processed | candidates | returned | approximate |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| serial_exact | 4 | 32 | simple | 186.020 | 88.996 | 2 | 2 | 1 | 1 | no |
| serial_exact | 4 | 32 | advanced | 89.691 | 25.484 | 2 | 2 | 1 | 1 | no |
| parallel_exact | 2 | 1 | simple | 915.259 | 882.364 | 2 | 2 | 1 | 1 | no |
| parallel_exact | 2 | 1 | advanced | 833.551 | 803.498 | 2 | 2 | 1 | 1 | no |
| parallel_budgeted | 2 | 1 | simple | 616.332 | 569.476 | 2 | 2 | 1 | 1 | no |
| parallel_budgeted | 2 | 1 | advanced | 1216.931 | 1175.543 | 2 | 2 | 1 | 1 | no |
| parallel_exact | 4 | 32 | simple | 58.908 | 24.486 | 2 | 2 | 1 | 1 | no |

The forced chunk size `1` results show Windows process-spawn overhead on tiny
datasets. The default chunk size `32` falls back to serial behavior for the
two-record fixture because the dataset fits in one chunk.

## Full Active Results

Full active cache state: local cached `active.tle`, `30,882` source records,
`15,351` fresh records loaded with `--max-tle-age-hours 72`, search window
`2026-05-26T20:00:00Z` for `10` minutes, result limit `10`.

The benchmark reports `tle_age_h=-33.280` because the newest TLE epoch in this
cache is later than the chosen search start. The record freshness check still
passes because future-dated epochs are not stale relative to that search start.

| mode | workers | chunk | total_ms | pass_ms | satellites | processed | candidates | filtered | returned | approximate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| serial_exact | 4 | 32 | 86618.571 | 51436.328 | 15351 | 15351 | 835 | 826 | 10 | no |
| parallel_exact | 2 | 32 | 140540.641 | 61174.911 | 15351 | 15351 | 835 | 826 | 10 | no |
| parallel_exact | 4 | 32 | 140502.642 | 41894.414 | 15351 | 15351 | 835 | 826 | 10 | no |
| parallel_budgeted | 4 | 32 | 14551.615 | 4004.694 | 15351 | 1536 | 74 | 66 | 10 | yes |

Exact parallel with four workers improved the pass-analysis stage relative to
serial, but total runtime was worse on this Windows run. The conservative
release policy therefore keeps exact serial as the default and keeps API
parallel execution disabled unless explicitly enabled by deployment settings.

Approximate budgeted parallel is much faster for broad active searches, but it
is not exact. It is appropriate for broad discovery searches where speed matters
more than proving that no unseen satellite could rank higher.

## Recommended Settings

Local development:

- Leave `TLEFINDER_PARALLEL_SEARCH_ENABLED` unset or set to `false`.
- Use `serial_exact` for correctness checks and small fixtures.
- Use the benchmark command with `--source cache` before changing defaults.

Operational deployment:

- Keep exact searches serial by default until deployment hardware shows a
consistent total-runtime speedup for exact parallel mode.
- If parallel search is enabled, start with `4` workers and chunk size `32`.
- Use approximate budgeted parallel only for broad `ACTIVE` searches without
strict hard filters.
- Use exact serial or exact parallel for OGS tracking decisions where an
approximate shortlist is not acceptable.
- Disable the feature quickly by setting `TLEFINDER_PARALLEL_SEARCH_ENABLED=0`
or by omitting `parallel_search` from direct Python callers.

TLE freshness:

- Cache files must be recent enough for the repository cache policy before they
are parsed.
- TLE record epochs should be close to the search window. The default record
freshness limit is `24` hours; these full-cache benchmarks used `72` hours only
to compare execution modes against the available local cache.
- OGS tracking searches should prefer current CelesTrak data and should treat
stale data as an operational error, not a no-result search.
