# TLE Finder API

\`tlefinder-api\` exposes the Core search engine through FastAPI and persists the ground-station list. It depends on the sibling \`../core\` project and uses the public \`tlefinder.core\` contract.

## Install and run

~~~powershell
cd api
poetry env use (pyenv which python)
poetry install
poetry run uvicorn tlefinder.api.app:app --reload --port 2626
~~~

The API is available at <http://127.0.0.1:2626>, Swagger at <http://127.0.0.1:2626/docs>, and the health check at <http://127.0.0.1:2626/healthz>.

The versioned routes are:

| Method | Route | Purpose |
| --- | --- | --- |
| \`GET\` | \`/api/v1/stations\` | Return saved stations |
| \`PUT\` | \`/api/v1/stations\` | Replace the saved station list |
| \`POST\` | \`/api/v1/search/simple\` | Search the active satellite group with standard criteria |
| \`POST\` | \`/api/v1/search/advanced\` | Search with explicit group, filters, and ranking controls |

See [HTTP API](docs/HTTP_API.md) for request examples, response shapes, errors, persistence, and environment variables.

## Run with the GUI

From the repository root, either use \`./scripts/dev.ps1\` for local development or start the complete application with Docker:

~~~powershell
docker compose up --detach --build --wait
~~~

The API is private in the default Compose configuration. Add \`compose.api-port.yaml\` when direct host access to port 2626 is required.

## Test and build

~~~powershell
poetry run pytest
poetry run pytest -m unit
poetry run pytest -m functional
poetry run pytest --cov=tlefinder.api --cov-report=term-missing
poetry build
~~~

## More documentation

- [Architecture](docs/ARCHITECTURE.md)
- [HTTP API](docs/HTTP_API.md)
