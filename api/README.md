# TLE Finder API

`tlefinder-api` owns the FastAPI HTTP adapter and station persistence. It declares the sibling `../core` project as its `tlefinder-core` dependency; its public Python import remains `tlefinder.api`.

Use the Python selected by global `pyenv`, then install and verify this project independently:

```powershell
cd api
poetry env use (pyenv which python)
poetry install
poetry run pytest
poetry run pytest -m unit
poetry run pytest -m functional
poetry run pytest --cov=tlefinder.api --cov-report=term-missing
poetry build
```

Start the API on the local development port with:

```powershell
poetry run uvicorn tlefinder.api.app:app --reload --port 2626
```

Runtime configuration is controlled by `TLEFINDER_STATION_STORE_PATH`, `TLEFINDER_PARALLEL_SEARCH_ENABLED`, `TLEFINDER_PARALLEL_WORKER_COUNT`, and `TLEFINDER_PARALLEL_CHUNK_SIZE`.

