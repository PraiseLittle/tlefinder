# TLE Finder Core

\`tlefinder-core\` is the reusable Python search engine. It validates a search request, loads fresh TLE data, finds visible passes, applies constraints, scores the candidates, and returns them in ranked order. It does not depend on the API or GUI.

## Install

~~~powershell
cd core
poetry env use (pyenv which python)
poetry install
~~~

Python 3.10 or newer is supported. The public import is \`tlefinder.core\`.

## Use from Python

Create a timezone-aware request and pass it to \`search_candidates\`:

~~~python
from datetime import datetime, timedelta, timezone

from tlefinder.core import (
    GroundStation,
    SatelliteGroup,
    SearchCriteria,
    SearchRequest,
    SearchWindow,
    TleAgeLimit,
    search_candidates,
)

request = SearchRequest(
    station=GroundStation(
        latitude=48.8367,
        longitude=2.3365,
        elevation_m=67,
    ),
    window=SearchWindow(
        start_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        duration_minutes=15,
    ),
    criteria=SearchCriteria(result_limit=5),
    satellite_group=SatelliteGroup.ACTIVE,
    tle_age_limit=TleAgeLimit.HOURS_24,
)

response = search_candidates(request)
for candidate in response.results:
    print(candidate.rank, candidate.satellite.tle.name, candidate.match_score)
~~~

The first search can download the selected CelesTrak dataset. Later searches reuse the local cache while it remains current.

\`find_best_candidate\` returns only the highest-ranked result. \`find_next_candidate\` scans forward in 30-minute windows until it finds a result or reaches its window limit.

## Test and build

~~~powershell
poetry run pytest
poetry run pytest -m unit
poetry run pytest -m functional
poetry run pytest --cov=tlefinder.core --cov=tlefinder.benchmarks --cov-report=term-missing
poetry build
~~~

## Benchmark

The default benchmark uses deterministic test fixtures and does not need the network:

~~~powershell
poetry run tlefinder-benchmark-core
~~~

Use \`poetry run tlefinder-benchmark-core --help\` for dataset, case, execution-mode, worker, chunk-size, and time-window options.

## More documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Search engine and benchmarking](docs/SEARCH_ENGINE.md)
