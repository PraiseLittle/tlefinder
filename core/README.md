# TLE Finder Core

`tlefinder-core` owns the reusable satellite-pass search engine and the `tlefinder-benchmark-core` command. Its public Python import remains `tlefinder.core`; it has no API or GUI dependency.

Use the Python selected by global `pyenv`, then install and verify this project independently:

```powershell
cd core
poetry env use (pyenv which python)
poetry install
poetry run pytest
poetry run pytest -m unit
poetry run pytest -m functional
poetry run pytest --cov=tlefinder.core --cov=tlefinder.benchmarks --cov-report=term-missing
poetry build
```

Run the deterministic benchmark fixtures with:

```powershell
poetry run tlefinder-benchmark-core
```

The benchmark defaults to `tests/fixtures` and does not download live TLE data unless a caller explicitly selects another source.

