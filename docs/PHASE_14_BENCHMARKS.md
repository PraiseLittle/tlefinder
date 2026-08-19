# Phase 14 Core Search Benchmark Baseline

The commands below are run from the current `core/` project root.

Captured on 2026-05-18 with `poetry run` using Python 3.10.11.

The benchmark command is:

```powershell
poetry run tlefinder-benchmark-core --groups active --start-at 2026-05-12T14:50:00Z --duration-minutes 12
```

Baseline inputs:

- station: latitude `48.8566`, longitude `2.3522`, elevation `35.0 m`
- TLE source group: `active`
- cache state: deterministic fixture file `tests/fixtures/active_sample.tle`
- local TLE records loaded: `2`
- window start: `2026-05-12T14:50:00Z`
- window duration: `12 minutes`
- result limit: `10`
- benchmark cases: `simple`, `advanced`
- parallel processing: disabled / not used

Baseline results:

| group | case | status | total_ms | pass_ms | satellites | candidates | filtered | returned |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| active | simple | results | 88.875 | 87.945 | 2 | 1 | 1 | 1 |
| active | advanced | results | 79.758 | 78.330 | 2 | 1 | 1 | 1 |

The script also supports fixture or local-cache runs for all configured groups:

```powershell
poetry run tlefinder-benchmark-core
poetry run tlefinder-benchmark-core --source cache --cache-dir tmp_tle_cache
```
