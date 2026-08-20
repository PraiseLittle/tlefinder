# TLE Finder

TLE Finder searches for satellite passes above an optical ground station and ranks the matches. The repository contains three independently buildable components:

- [Core](core/README.md) — Python search engine and benchmark command.
- [API](api/README.md) — FastAPI service and station persistence.
- [GUI](gui/README.md) — React web interface.

The API depends on Core. The GUI communicates with the API over HTTP.

## Run with Docker

Docker Desktop or Docker Engine with Compose can run the complete application:

~~~powershell
docker compose up --detach --build --wait
~~~

Open <http://127.0.0.1:2627>.

Re-run the same command to rebuild after a code change. Stop the application with:

~~~powershell
docker compose down
~~~

Stations and downloaded TLE files remain in named Docker volumes when the containers are stopped or rebuilt.

The API normally stays inside the Compose network. To expose it on the local machine as well:

~~~powershell
docker compose -f compose.yaml -f compose.api-port.yaml up --detach --build --wait
~~~

Swagger is then available at <http://127.0.0.1:2626/docs>.

## Run for development

Install Python 3.10 or newer, pyenv, Poetry, Node.js 22, npm, and PowerShell 7. Install each component once:

~~~powershell
cd core
poetry env use (pyenv which python)
poetry install

cd ../api
poetry env use (pyenv which python)
poetry install

cd ../gui
npm ci

cd ..
~~~

Start the API and GUI together in the current terminal:

~~~powershell
./scripts/dev.ps1
~~~

Open <http://127.0.0.1:2627>. The API runs on port 2626 and the GUI on port 2627. Press Ctrl+C to stop both processes. Use \`./scripts/dev.ps1 -NoReload\` to disable automatic API reloads.

The component READMEs explain how to run Core, API, or GUI independently.

## Verify the repository

Run every component test, build both Python packages, inspect their wheels, typecheck the GUI, and create its production build:

~~~powershell
./scripts/verify.ps1
~~~

See [CONTRIBUTING.md](CONTRIBUTING.md) for component ownership and dependency rules.
