# Phase 23 - API and GUI Containerization

> Mandatory rule: Always write the unit, configuration, and smoke tests before adding or changing container implementation. It is forbidden to weaken those tests after the first Dockerfile, proxy configuration, or Compose service is added without permission.

> Environment rule: Build the Python API from the API Poetry lockfile and its declared Core dependency. Build the GUI from the committed npm lockfile. Use Docker Compose for the local multi-container workflow.

> Dependency rule: This phase starts only after phase 22 has produced independent top-level `core`, `api`, and `gui` projects with passing component test suites.

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
```

Only the GUI must be published for the normal user workflow. Publishing the API port is allowed as a documented development option, but container-to-container traffic must use the Compose service name and internal network.

## Tasks

- [ ] Write container contract tests before creating the images.
  - [ ] Add an API configuration test proving the container defaults bind Uvicorn to `0.0.0.0:2626` without changing local non-container defaults.
  - [ ] Add an API configuration test proving `TLEFINDER_STATION_STORE_PATH=/data/stations.yaml` is honored.
  - [ ] Add an API liveness-route test for `GET /healthz` that requires no station-store mutation, TLE download, or external network access.
  - [ ] Add a GUI configuration test proving the production client keeps `/api/v1` as its browser-visible base URL.
  - [ ] Add reverse-proxy configuration checks for `/api/`, SPA history fallback, and preservation of request paths and status codes.
  - [ ] Add Compose configuration checks for service names, ports, health checks, named-volume persistence, and dependency ordering.
  - [ ] Add image-content checks that reject source caches, test caches, local virtual environments, `node_modules`, secrets, and development-only files in final images.
- [ ] Create the API container build.
  - [ ] Add `api/Dockerfile` using separate dependency/build and runtime stages.
  - [ ] Use a supported slim Python base image compatible with the project's selected Python version and pin the image version deliberately.
  - [ ] Build or install `tlefinder-core` from `core` and install `tlefinder-api` from `api` using their locked dependency definitions.
  - [ ] Keep compilers, Poetry, build caches, test dependencies, and source-control metadata out of the final runtime stage.
  - [ ] Run the API as a non-root user with a read-only application directory.
  - [ ] Create or grant access only to the `/data` location required for station persistence.
  - [ ] Start Uvicorn with `tlefinder.api.app:app`, host `0.0.0.0`, port `2626`, no reload mode, and an explicit production worker policy.
  - [ ] Use exec-form startup so termination signals reach Uvicorn and shutdown completes cleanly.
  - [ ] Add an API health check that calls `/healthz` with tooling already present in the final image.
  - [ ] Add `api/.dockerignore` or an equivalent root build-context ignore file covering Python caches, virtual environments, test artifacts, local data, and unrelated GUI files.
- [ ] Make API runtime configuration container-safe.
  - [ ] Add `GET /healthz` as a liveness endpoint outside `/api/v1`; keep it independent of TLE freshness and external services.
  - [ ] Set the container station-store default to `/data/stations.yaml` through Compose rather than hard-coding a container path into normal application behavior.
  - [ ] Preserve all existing `/api/v1` routes, OpenAPI schemas, error envelopes, and search behavior.
  - [ ] Document environment variables for station storage, parallel execution, worker count, chunk size, logging, and any Uvicorn process settings.
  - [ ] Ensure logs go to standard output/error and do not contain station-store contents, secrets, or excessive per-satellite diagnostics.
  - [ ] Verify a read-only root filesystem is feasible apart from explicitly mounted writable runtime locations; document any required temporary directory.
- [ ] Create the GUI container build.
  - [ ] Add `gui/Dockerfile` with a Node build stage and a separate minimal web-server runtime stage.
  - [ ] Install frontend dependencies with `npm ci` from the committed lockfile.
  - [ ] Run GUI unit tests, type checks, and the production build before copying artifacts into the runtime stage.
  - [ ] Copy only the generated static assets and reviewed web-server configuration into the final image.
  - [ ] Run the web server as a non-root user and listen on internal port `8080`.
  - [ ] Configure `index.html` fallback for client-side routes without masking missing static assets.
  - [ ] Proxy `/api/` to `http://api:2626` while preserving the full `/api/v1/...` path, request body, query string, and relevant forwarding headers.
  - [ ] Do not compile `http://api:2626` into browser JavaScript; the Compose service name is resolvable only inside the Docker network.
  - [ ] Add cache headers that keep fingerprinted assets cacheable while preventing stale `index.html` deployments.
  - [ ] Add a GUI health check for the served root document.
  - [ ] Add `gui/.dockerignore` covering `node_modules`, build output, caches, local environment files, test artifacts, and unrelated Python files.
- [ ] Add the Docker Compose application workflow.
  - [ ] Add the root `compose.yaml` with `api` and `gui` services built from the monorepo context.
  - [ ] Connect both services to a private application network and address the backend internally as `api:2626`.
  - [ ] Publish the GUI on a documented host port, defaulting to `2627` to preserve the current local URL.
  - [ ] Keep API port `2626` internal by default and document an opt-in development override when direct OpenAPI access is needed.
  - [ ] Mount a named volume at `/data` for the API station YAML file.
  - [ ] Make GUI readiness depend on the API health check rather than process start alone.
  - [ ] Add sensible restart and stop-grace-period settings so Uvicorn and the web server shut down cleanly.
  - [ ] Avoid host bind mounts, reload servers, and development dependency installation in the default Compose file.
  - [ ] Render and validate the fully resolved Compose configuration in automated checks.
- [ ] Integrate image verification into component CI.
  - [ ] Extend `.github/workflows/api.yml` to test the API, build the API image, and run its container smoke test when API, Core, or relevant container files change.
  - [ ] Extend `.github/workflows/gui.yml` to test and build the GUI, build the GUI image, and run its container smoke test when GUI or relevant container files change.
  - [ ] Keep `.github/workflows/core.yml` focused on Core packaging and tests; make API CI consume its result through the declared Core dependency rather than duplicating Core source.
  - [ ] Run Compose integration tests when `compose.yaml`, either Dockerfile, proxy configuration, or shared workflow configuration changes.
  - [ ] Build images on pull requests without publishing them; make registry publication a separately authorized release action.
- [ ] Add container integration and persistence tests.
  - [ ] Build both images from a clean Docker cache and fail on lockfile or missing-file errors.
  - [ ] Inspect the API image to confirm Core and API import successfully and GUI/Node artifacts are absent.
  - [ ] Inspect the GUI image to confirm it contains static output but no Python environment, source `node_modules`, or API source.
  - [ ] Start the stack and wait for both health checks with a bounded timeout.
  - [ ] Request `/healthz` through the GUI proxy and verify the response comes from the API container.
  - [ ] Request `/openapi.json` through the GUI proxy and verify the four existing `/api/v1` operations remain present.
  - [ ] Request a non-root GUI route directly and verify SPA fallback returns the GUI rather than a web-server 404.
  - [ ] Write a station list through the proxied API, recreate the API container, and verify the named volume preserves the list.
  - [ ] Verify an invalid station update still preserves the previous file inside the named volume.
  - [ ] Exercise one mocked or fixture-backed search path without depending on a live TLE provider.
  - [ ] Stop the stack and confirm no application containers remain running.
- [ ] Harden and size the images.
  - [ ] Scan both final images for known high-severity dependency and operating-system vulnerabilities using the project's chosen scanner.
  - [ ] Review all base-image and application dependency versions and record any accepted vulnerability exception.
  - [ ] Confirm both services run without root privileges or extra Linux capabilities.
  - [ ] Confirm no secret, local `.env` file, station database, Poetry credential, npm credential, or Git metadata is present in either image.
  - [ ] Record final compressed and unpacked image sizes and remove avoidable build artifacts.
  - [ ] Verify API CPU and memory limits do not break configured process-pool search behavior; document the relationship between Uvicorn workers and Core parallel workers.
- [ ] Document container operation.
  - [ ] Add exact commands to build, start, inspect, stop, and update the stack.
  - [ ] Document the GUI URL, optional direct API URL, health endpoints, log commands, and expected startup order.
  - [ ] Document station-volume backup, restore, and removal, clearly marking volume removal as destructive.
  - [ ] Document configuration overrides without committing secrets or machine-specific paths.
  - [ ] Document how to rebuild when Core, API, GUI, or a lockfile changes.
  - [ ] Add troubleshooting notes for occupied ports, unhealthy services, proxy errors, file permissions, and stale images.
- [ ] Run final verification.
  - [ ] Run Core, API, and GUI component test suites before building images.
  - [ ] Build the API and GUI images with the documented commands.
  - [ ] Run all container configuration, smoke, proxy, and persistence tests.
  - [ ] Run GUI type checks and production build from the locked dependency set.
  - [ ] Confirm a new developer can start the complete application with one documented Compose command.
  - [ ] Confirm the non-container development commands from phase 22 still work.

## Done When

- [ ] The API and GUI each have reproducible multi-stage container builds whose final images contain only runtime requirements.
- [ ] Both containers run as non-root users, expose working health checks, handle termination cleanly, and contain no known unreviewed high-severity vulnerabilities.
- [ ] The GUI serves the production Vite build and proxies `/api/v1` to the API through the private Compose network without exposing an internal hostname to the browser.
- [ ] The API uses the installed Core project, preserves the existing HTTP contract, and stores stations on a persistent named volume.
- [ ] The full application starts through one documented Docker Compose command and is usable through the GUI host port.
- [ ] Container smoke, proxy, restart-persistence, component, type-check, and production-build tests all pass without live external TLE access.
- [ ] Image contents, runtime configuration, volume lifecycle, and troubleshooting steps are documented.
