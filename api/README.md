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

The container launcher is `python -m tlefinder.api.server`. Its local defaults remain `127.0.0.1:2626` with one worker; Compose overrides the host to `0.0.0.0`, persists the station store at `/data/stations.yaml`, and persists downloaded TLE datasets under `/tle-cache`.

Runtime configuration is controlled by `TLEFINDER_STATION_STORE_PATH`, `TLEFINDER_TLE_CACHE_DIR`, `TLEFINDER_PARALLEL_SEARCH_ENABLED`, `TLEFINDER_PARALLEL_WORKER_COUNT`, `TLEFINDER_PARALLEL_CHUNK_SIZE`, `TLEFINDER_UVICORN_HOST`, `TLEFINDER_UVICORN_PORT`, `TLEFINDER_UVICORN_WORKERS`, and `TLEFINDER_LOG_LEVEL`.

From the repository root, start the full application with `docker compose up --detach --build --wait`. Use the opt-in API-port override for Swagger at `http://127.0.0.1:2626/docs`:

```powershell
docker compose -f compose.yaml -f compose.api-port.yaml up --detach --build --wait
```

See [`../docs/CONTAINERS.md`](../docs/CONTAINERS.md) for the full operational guide.

