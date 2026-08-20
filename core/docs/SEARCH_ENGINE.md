# Search Engine and Benchmarking

## TLE acquisition and freshness

Core supports the CelesTrak \`active\`, \`visual\`, and \`amateur\` groups. By default, datasets are stored under \`~/.cache/tlefinder/tle\`.

A cache file can be reused for two hours. If it is missing or older, Core asks CelesTrak for the selected group and replaces the cache. A failed refresh does not silently use a cache that has exceeded this cache window.

Cache age and TLE epoch age are separate checks:

- Cache age controls when the source is contacted again.
- TLE age compares each record epoch with the requested search time.
- The normal limit is 24 hours; requests can explicitly allow one week.

Tests and callers can replace the cache directory, HTTP client, source configuration, and maximum age. This keeps the search pipeline deterministic without embedding test behavior in production code.

## Time and pass geometry

Search start times must contain an explicit UTC offset. Core normalizes them to UTC and builds the end time from the requested duration.

Pass analysis uses Skyfield and a 10-degree optical horizon. It searches far enough around the requested interval to recognize passes that begin before the interval or end after it. A pass is eligible when its visible portion overlaps the requested window.

For each pass, Core records:

- UTC start, culmination, and end times.
- Start, culmination, and end azimuth.
- Culmination apparent altitude.
- Mean satellite altitude.
- Angular separation from the Sun.

Metric calculation is deferred until it is needed by a filter or by a returned result.

## Filtering, scoring, and ranking

Hard filters can constrain:

- Culmination altitude by range or target and tolerance.
- Start, culmination, and end azimuth by circular target and tolerance.
- Satellite altitude by range.
- Sun proximity by range.

Candidates that pass the hard filters receive a 0–100 score. Pass-duration fit and start-time fit are always included. Enabled culmination, azimuth, and Sun preferences add equally weighted components; disabled criteria add no hidden weight.

After scoring, Core:

1. Removes candidates below \`score_threshold\`.
2. Sorts by descending score.
3. Breaks ties by earlier pass start and then NORAD catalog number.
4. Assigns one-based ranks.
5. Returns at most \`result_limit\` candidates.

## Execution modes

Serial exact execution evaluates the complete selected dataset in the current process.

Parallel exact execution divides geometry work into deterministic chunks processed by a process pool. Worker count is bounded and chunk size is validated. Merged candidates use the same filtering, scoring, and ranking path as serial execution.

Approximate budgeted execution can stop geometry work after collecting a candidate budget. It is intended for broad active-group searches and reports that unseen satellites may have scored higher. Core disables the budget automatically when the group or strict filters make it unsafe. The API simple-search route requests this mode; advanced searches remain exact.

Diagnostics report the actual execution mode, processed satellite and candidate counts, chunk scheduling, skipped records, stage timings, and whether approximate budgeting was enabled or disabled.

## Benchmark command

Run the repeatable fixture benchmark:

~~~powershell
poetry run tlefinder-benchmark-core
~~~

Compare execution modes:

~~~powershell
poetry run tlefinder-benchmark-core --execution-mode serial_exact
poetry run tlefinder-benchmark-core --execution-mode parallel_exact --parallel-workers 4 --parallel-chunk-size 32
poetry run tlefinder-benchmark-core --execution-mode parallel_budgeted --parallel-workers 4 --parallel-chunk-size 32
~~~

The command accepts:

- \`--source fixtures\` for committed deterministic data.
- \`--source cache --cache-dir PATH\` for a local dataset.
- \`--groups active,visual,amateur\`.
- \`--cases simple,advanced\`.
- An explicit start, duration, and maximum TLE age.
- Process-pool worker and chunk-size settings for parallel modes.

Use \`poetry run tlefinder-benchmark-core --help\` as the authoritative option list. Benchmark output reports timings and search diagnostics; it is an observation tool, not a persisted compatibility contract.
