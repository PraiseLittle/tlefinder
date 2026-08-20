# Core Architecture

## Responsibility

Core owns the satellite-pass domain and the complete search pipeline. It can be installed, tested, built, and imported without the API or GUI.

The public package is \`tlefinder.core\`. API code may depend on that package, but Core must not import \`tlefinder.api\` or any frontend code.

## Package layout

| Module | Responsibility |
| --- | --- |
| \`models.py\` | Dataclasses and enums shared by the search workflow |
| \`validation.py\` | Domain validation for stations, windows, criteria, groups, and TLE age |
| \`time_utils.py\` | Explicit-offset datetime normalization and interval construction |
| \`tle_repository.py\` | CelesTrak download, cache, parsing, and epoch freshness |
| \`pass_analysis.py\` | Skyfield propagation, pass-event detection, geometry, and metrics |
| \`filtering.py\` | Hard geometry and metric constraints |
| \`scoring.py\` | Deterministic 0–100 soft-preference score |
| \`ranking.py\` | Score threshold, stable ordering, rank assignment, and result limit |
| \`engine.py\` | Public orchestration entry points and diagnostics |
| \`errors.py\` | Expected Core exception hierarchy |

\`tlefinder.core.__init__\` is the supported import surface. Consumers should import public models, validation helpers, and search entry points from there instead of depending on private helpers.

## Public contract

A search is represented by \`SearchRequest\`:

- \`GroundStation\` supplies latitude, longitude, and elevation.
- \`SearchWindow\` supplies a timezone-aware start and a duration of at most 30 minutes.
- \`SearchCriteria\` contains optional range and target/tolerance constraints, a score threshold, and a result limit.
- \`SatelliteGroup\` selects \`active\`, \`visual\`, or \`amateur\`.
- \`TleAgeLimit\` selects a 24-hour or one-week record-epoch limit.

\`search_candidates\` returns a \`SearchResponse\` whose status is \`results\` or \`no_result\`. Each \`CandidatePass\` combines the satellite and TLE, pass geometry, derived metrics, match score, rank, and diagnostics.

The convenience entry points \`find_best_candidate\` and \`find_next_candidate\` use the same request and execution options.

## Search data flow

1. Validate the request and normalize its start time to UTC.
2. Load a current cached TLE dataset or download it from CelesTrak.
3. Reject TLE records whose epochs exceed the selected age limit.
4. Build one pass-analysis session for the station and interval.
5. Detect candidate pass geometry for every applicable satellite.
6. Apply geometry-only filters before computing optional expensive metrics.
7. Compute satellite altitude and Sun proximity when required.
8. Apply metric filters, calculate match scores, and apply the score threshold.
9. Sort deterministically, assign ranks, and apply the result limit.
10. Complete response metrics and return stage, dataset, optimization, and pass-analysis diagnostics.

## Failures and diagnostics

Expected failures derive from \`TleFinderError\`:

- \`ValidationError\` for an invalid public request.
- \`TleLoadError\` for download, cache, or parsing failures.
- \`TleFreshnessError\` when no TLE record satisfies the requested age.
- \`PropagationError\` for satellite propagation failures.
- \`SearchExecutionError\` for invalid search state.

Individual unusable satellite records can be skipped and described in bounded diagnostics without failing every result. Response diagnostics are JSON-friendly so the API can serialize them without translating private Python objects.

## Tests and packaging

Unit tests mirror the Core modules under \`tests/unit\`. Functional tests verify packaging and complete workflows. Deterministic TLE files under \`tests/fixtures\` are shared by tests and the default benchmark.

Poetry builds the independent \`tlefinder-core\` distribution. Core and API share the implicit \`tlefinder\` namespace; do not add \`src/tlefinder/__init__.py\`.
