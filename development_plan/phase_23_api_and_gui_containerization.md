# Phase 23 - API and GUI Containerization

> Mandatory rule: Always write the unit, configuration, and smoke tests before adding or changing container implementation. It is forbidden to weaken those tests after the first Dockerfile, proxy configuration, or Compose service is added without permission.

> Environment rule: Build the Python API from the API Poetry lockfile and its declared Core dependency. Build the GUI from the committed npm lockfile. Use Docker Compose for the local multi-container workflow.

> Dependency rule: This phase starts only after phase 22 has produced independent top-level `core`, `api`, and `gui` projects with passing component test suites.

> Scope decision (2026-08-19): These containers are for local use only. Image publication and mandatory third-party vulnerability scanning are outside this phase; dependency review and runtime hardening remain required.

## Goal

Package the API and GUI as reproducible, production-oriented containers and provide one Docker Compose workflow that connects them without exposing internal service addresses to the browser.

The API container runs the existing FastAPI application and persists the station store outside its writable container layer. The GUI container serves the Vite production build through a small web server and proxies `/api` requests to the API service, preserving the GUI's same-origin `/api/v1` contract.

## Target Layout

```text
core/
  ...
  tests/
api/
  ...
  tests/
  Dockerfile
  .dockerignore
gui/
  ...
  tests/
  Dockerfile
  .dockerignore
compose.yaml
README.md
.github/
  workflows/
    core.yml
    api.yml
    gui.yml
```

## Target Runtime

```text
Browser
  -> GUI container :8080
       -> static Vite assets
       -> /api/* reverse proxy
            -> API container :2626
                 -> tlefinder.api.app:app
                 -> installed tlefinder-core package
                 -> /data/stations.yaml on a named volume
                 -> /tle-cache/*.tle on a separate named volume
```

Only the GUI must be published for the normal user workflow. Publishing the API port is allowed as a documented development option, but container-to-container traffic must use the Compose service name and internal network.

## Tasks

- [x] Write container contract tests before creating the images.
  - [x] Add an API configuration test proving the container defaults bind Uvicorn to `0.0.0.0:2626` without changing local non-container defaults.
  - [x] Add an API configuration test proving `TLEFINDER_STATION_STORE_PATH=/data/stations.yaml` is honored.
  - [x] Add an API liveness-route test for `GET /healthz` that requires no station-store mutation, TLE download, or external network access.
  - [x] Add a GUI configuration test proving the production client keeps `/api/v1` as its browser-visible base URL.
  - [x] Add reverse-proxy configuration checks for `/api/`, SPA history fallback, and preservation of request paths and status codes.
  - [x] Add Compose configuration checks for service names, ports, health checks, named-volume persistence, and dependency ordering.
  - [x] Add image-content checks that reject source caches, test caches, local virtual environments, `node_modules`, secrets, and development-only files in final images.
- [x] Create the API container build.
  - [x] Add `api/Dockerfile` using separate dependency/build and runtime stages.
  - [x] Use a supported slim Python base image compatible with the project's selected Python version and pin the image version deliberately.
  - [x] Build or install `tlefinder-core` from `core` and install `tlefinder-api` from `api` using their locked dependency definitions.
  - [x] Keep compilers, Poetry, build caches, test dependencies, and source-control metadata out of the final runtime stage.
  - [x] Run the API as a non-root user with a read-only application directory.
  - [x] Create or grant access only to the `/data` location required for station persistence.
  - [x] Start Uvicorn with `tlefinder.api.app:app`, host `0.0.0.0`, port `2626`, no reload mode, and an explicit production worker policy.
  - [x] Use exec-form startup so termination signals reach Uvicorn and shutdown completes cleanly.
  - [x] Add an API health check that calls `/healthz` with tooling already present in the final image.
  - [x] Add `api/.dockerignore` or an equivalent root build-context ignore file covering Python caches, virtual environments, test artifacts, local data, and unrelated GUI files.
- [x] Make API runtime configuration container-safe.
  - [x] Add `GET /healthz` as a liveness endpoint outside `/api/v1`; keep it independent of TLE freshness and external services.
  - [x] Set the container station-store default to `/data/stations.yaml` through Compose rather than hard-coding a container path into normal application behavior.
  - [x] Preserve all existing `/api/v1` routes, OpenAPI schemas, error envelopes, and search behavior.
  - [x] Document environment variables for station storage, parallel execution, worker count, chunk size, logging, and any Uvicorn process settings.
  - [x] Ensure logs go to standard output/error and do not contain station-store contents, secrets, or excessive per-satellite diagnostics.
  - [x] Verify a read-only root filesystem is feasible apart from explicitly mounted writable runtime locations; document any required temporary directory.
- [x] Create the GUI container build.
  - [x] Add `gui/Dockerfile` with a Node build stage and a separate minimal web-server runtime stage.
  - [x] Install frontend dependencies with `npm ci` from the committed lockfile.
  - [x] Run GUI unit tests, type checks, and the production build before copying artifacts into the runtime stage.
  - [x] Copy only the generated static assets and reviewed web-server configuration into the final image.
  - [x] Run the web server as a non-root user and listen on internal port `8080`.
  - [x] Configure `index.html` fallback for client-side routes without masking missing static assets.
  - [x] Proxy `/api/` to `http://api:2626` while preserving the full `/api/v1/...` path, request body, query string, and relevant forwarding headers.
  - [x] Do not compile `http://api:2626` into browser JavaScript; the Compose service name is resolvable only inside the Docker network.
  - [x] Add cache headers that keep fingerprinted assets cacheable while preventing stale `index.html` deployments.
  - [x] Add a GUI health check for the served root document.
  - [x] Add `gui/.dockerignore` covering `node_modules`, build output, caches, local environment files, test artifacts, and unrelated Python files.
- [x] Add the Docker Compose application workflow.
  - [x] Add the root `compose.yaml` with `api` and `gui` services built from the monorepo context.
  - [x] Connect both services to a private application network and address the backend internally as `api:2626`.
  - [x] Publish the GUI on a documented host port, defaulting to `2627` to preserve the current local URL.
  - [x] Keep API port `2626` internal by default and document an opt-in development override when direct OpenAPI access is needed.
  - [x] Mount a named volume at `/data` for the API station YAML file.
  - [x] Mount a separate named volume at `/tle-cache` and pass it explicitly to Core for downloaded TLE persistence.
  - [x] Make GUI readiness depend on the API health check rather than process start alone.
  - [x] Add sensible restart and stop-grace-period settings so Uvicorn and the web server shut down cleanly.
  - [x] Avoid host bind mounts, reload servers, and development dependency installation in the default Compose file.
  - [x] Render and validate the fully resolved Compose configuration in automated checks.
- [x] Integrate image verification into component CI.
  - [x] Extend `.github/workflows/api.yml` to test the API, build the API image, and run its container smoke test when API, Core, or relevant container files change.
  - [x] Extend `.github/workflows/gui.yml` to test and build the GUI, build the GUI image, and run its container smoke test when GUI or relevant container files change.
  - [x] Keep `.github/workflows/core.yml` focused on Core packaging and tests; make API CI consume its result through the declared Core dependency rather than duplicating Core source.
  - [x] Run Compose integration tests when `compose.yaml`, either Dockerfile, proxy configuration, or shared workflow configuration changes.
  - [x] Build images on pull requests without publishing them; make registry publication a separately authorized release action.
- [x] Add container integration and persistence tests.
  - [x] Build both images from a clean Docker cache and fail on lockfile or missing-file errors.
  - [x] Inspect the API image to confirm Core and API import successfully and GUI/Node artifacts are absent.
  - [x] Inspect the GUI image to confirm it contains static output but no Python environment, source `node_modules`, or API source.
  - [x] Start the stack and wait for both health checks with a bounded timeout.
  - [x] Request `/healthz` through the GUI proxy and verify the response comes from the API container.
  - [x] Request `/openapi.json` through the GUI proxy and verify the four existing `/api/v1` operations remain present.
  - [x] Request a non-root GUI route directly and verify SPA fallback returns the GUI rather than a web-server 404.
  - [x] Write a station list through the proxied API, recreate the API container, and verify the named volume preserves the list.
  - [x] Verify an invalid station update still preserves the previous file inside the named volume.
  - [x] Exercise one mocked or fixture-backed search path without depending on a live TLE provider.
  - [x] Recreate the API container and verify the fixture-backed TLE cache survives and remains usable.
  - [x] Stop the stack and confirm no application containers remain running.
- [x] Harden and size the images.
  - [x] Review all base-image and application dependency versions and record any accepted vulnerability exception.
  - [x] Confirm both services run without root privileges or extra Linux capabilities.
  - [x] Confirm no secret, local `.env` file, station database, Poetry credential, npm credential, or Git metadata is present in either image.
  - [x] Record final compressed and unpacked image sizes and remove avoidable build artifacts.
  - [x] Verify API CPU and memory limits do not break configured process-pool search behavior; document the relationship between Uvicorn workers and Core parallel workers.
- [x] Document container operation.
  - [x] Add exact commands to build, start, inspect, stop, and update the stack.
  - [x] Document the GUI URL, optional direct API URL, health endpoints, log commands, and expected startup order.
  - [x] Document station and TLE-cache volume backup, restore, and removal, clearly marking volume removal as destructive.
  - [x] Document configuration overrides without committing secrets or machine-specific paths.
  - [x] Document how to rebuild when Core, API, GUI, or a lockfile changes.
  - [x] Add troubleshooting notes for occupied ports, unhealthy services, proxy errors, file permissions, and stale images.
- [x] Run final verification.
  - [x] Run Core, API, and GUI component test suites before building images.
  - [x] Build the API and GUI images with the documented commands.
  - [x] Run all container configuration, smoke, proxy, and persistence tests.
  - [x] Run GUI type checks and production build from the locked dependency set.
  - [x] Confirm a new developer can start the complete application with one documented Compose command.
  - [x] Confirm the non-container development commands from phase 22 still work.

## Done When

- [x] The API and GUI each have reproducible multi-stage container builds whose final images contain only runtime requirements.
- [x] Both containers run as non-root users, expose working health checks, and handle termination cleanly.
- [x] The GUI serves the production Vite build and proxies `/api/v1` to the API through the private Compose network without exposing an internal hostname to the browser.
- [x] The API uses the installed Core project, preserves the existing HTTP contract, and stores stations and downloaded TLE datasets on persistent named volumes.
- [x] The full application starts through one documented Docker Compose command and is usable through the GUI host port.
- [x] Container smoke, proxy, restart-persistence, component, type-check, and production-build tests all pass without live external TLE access.
- [x] Image contents, runtime configuration, volume lifecycle, and troubleshooting steps are documented.
