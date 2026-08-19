# Container operation

The default Compose application contains a private `application` network, an internal API service, a GUI published on host port `2627`, the `station-data` named volume, and the `tle-cache` named volume. There are no source bind mounts, reload servers, or development dependencies in either final image.

## Build, start, inspect, stop, and update

Run these commands from the repository root:

```powershell
# Build both pinned, multi-stage images from their committed lockfiles.
docker compose build

# Start API first, wait for its health check, then start GUI.
docker compose up --detach --wait

# Inspect state and follow logs written to standard output/error.
docker compose ps
docker compose logs --follow api gui

# Stop containers and the network while preserving both data volumes.
docker compose down

# Pull pinned base manifests, rebuild changed components, and recreate safely.
docker compose build --pull
docker compose up --detach --wait
```

The normal entry point is `http://127.0.0.1:2627`. The API liveness endpoint is proxied at `http://127.0.0.1:2627/healthz`, and its OpenAPI document is proxied at `http://127.0.0.1:2627/openapi.json`. Startup is API container → successful API health check → GUI container → successful GUI root-document health check.

The API is not published by default. For loopback-only direct API and interactive-doc access during development:

```powershell
docker compose -f compose.yaml -f compose.api-port.yaml up --detach --build --wait
```

The direct URLs are `http://127.0.0.1:2626/healthz`, `http://127.0.0.1:2626/docs`, and `http://127.0.0.1:2626/openapi.json`. Set `TLEFINDER_API_PORT` before the command to choose another host port. Container traffic still uses `api:2626`.

Rebuild `api` after Core, API, either Python manifest, or either Poetry lockfile changes. Rebuild `gui` after GUI source, `package.json`, `package-lock.json`, `nginx.conf`, or its Dockerfile changes:

```powershell
docker compose build api
docker compose build gui
docker compose up --detach --wait
```

Use `docker compose build --no-cache` to diagnose stale layers or prove a clean locked build. Images are built on pull requests but are never published; registry publication requires a separate release action.

## Runtime configuration

Compose reads the following host environment variables. Keep machine-specific values in an uncommitted local environment; never commit secrets or credentials. No current variable needs a secret value.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TLEFINDER_GUI_PORT` | `2627` | Published GUI host port. |
| `TLEFINDER_API_PORT` | `2626` | Host port used only by `compose.api-port.yaml`. |
| `TLEFINDER_STATION_STORE_PATH` | `/data/stations.yaml` in Compose | API station YAML; Compose intentionally fixes this to the volume. |
| `TLEFINDER_TLE_CACHE_DIR` | `/tle-cache` in Compose | Persistent downloaded TLE datasets; Compose intentionally fixes this to its own volume. |
| `TLEFINDER_PARALLEL_SEARCH_ENABLED` | `false` | Enables Core process-pool search. |
| `TLEFINDER_PARALLEL_WORKER_COUNT` | `4` | Core child-process ceiling per search. |
| `TLEFINDER_PARALLEL_CHUNK_SIZE` | `32` | Satellites assigned per Core work chunk. |
| `TLEFINDER_UVICORN_HOST` | `0.0.0.0` in Compose | Container bind address; non-container default is `127.0.0.1`. |
| `TLEFINDER_UVICORN_PORT` | `2626` | Internal API listen port. |
| `TLEFINDER_UVICORN_WORKERS` | `1` | Uvicorn application processes. |
| `TLEFINDER_LOG_LEVEL` | `info` | Uvicorn log level (`debug`, `info`, `warning`, `error`, or `critical`). |

Example PowerShell override:

```powershell
$env:TLEFINDER_GUI_PORT = "3627"
$env:TLEFINDER_PARALLEL_SEARCH_ENABLED = "true"
$env:TLEFINDER_PARALLEL_WORKER_COUNT = "2"
docker compose up --detach --build --wait
```

Keep Uvicorn at one worker when Core parallel search is enabled unless capacity tests justify otherwise. At peak concurrency, `N` Uvicorn workers can each start up to `P` Core workers, producing roughly `N × P` CPU-bound child processes plus the API parents. For a two-CPU/1 GiB allocation, use one Uvicorn worker and at most two Core workers. The default Compose file intentionally sets no CPU or memory ceiling so Docker Desktop and server operators can apply platform-appropriate limits without silently breaking process-pool search. The reviewed two-CPU/1 GiB policy is available as an opt-in override:

```powershell
docker compose -f compose.yaml -f compose.resources.yaml up --detach --build --wait
```

Both root filesystems are read-only and both services drop all Linux capabilities. The API writes station data under `/data`, downloaded TLE datasets under `/tle-cache`, and other transient files under its `/tmp` tmpfs; the GUI writes only Nginx temporary files under its `/tmp` tmpfs. Logs contain request metadata and operational errors, not station-store bodies or credentials.

The TLE volume improves restart behavior and avoids unnecessary downloads, but it does not disable freshness validation. When online, the API refreshes the cache according to Core policy. Searches still reject TLE records older than their selected 24-hour or one-week limit.

## Persistent-volume backup, restore, and removal

Stop writes before backup, then archive the single persisted file. In PowerShell, `${PWD}` expands to the repository directory:

```powershell
docker compose stop api gui
docker run --rm --volume tlefinder_station-data:/data:ro --volume "${PWD}:/backup" alpine:3.21.3 tar -czf /backup/tlefinder-stations.tgz -C /data stations.yaml
docker compose start api gui
```

After at least one search has populated the TLE cache, back it up separately:

```powershell
docker compose stop api gui
docker run --rm --volume tlefinder_tle-cache:/tle-cache:ro --volume "${PWD}:/backup" alpine:3.21.3 tar -czf /backup/tlefinder-tle-cache.tgz -C /tle-cache .
docker compose start api gui
```

Restore only after stopping the stack. The restore command replaces `/data/stations.yaml` in the named volume:

```powershell
docker compose down
docker run --rm --volume tlefinder_station-data:/data --volume "${PWD}:/backup:ro" alpine:3.21.3 sh -c "rm -f /data/stations.yaml && tar -xzf /backup/tlefinder-stations.tgz -C /data"
docker compose up --detach --wait
```

Restore the TLE cache independently after stopping the stack:

```powershell
docker compose down
docker run --rm --volume tlefinder_tle-cache:/tle-cache --volume "${PWD}:/backup:ro" alpine:3.21.3 sh -c "rm -rf /tle-cache/* && tar -xzf /backup/tlefinder-tle-cache.tgz -C /tle-cache"
docker compose up --detach --wait
```

Destructive: the following command permanently removes the application containers, every saved station in `station-data`, and every downloaded dataset in `tle-cache`. Back up either volume first if its data matters.

```powershell
docker compose down --volumes
```

## Verification and image review

The configuration checks run with the API tests. The bounded integration script creates its own project and volumes, verifies image contents, health, proxy status/path preservation, OpenAPI operations, SPA fallback, offline fixture-backed search, atomic invalid updates, station persistence, and TLE-cache persistence across API recreation, and then removes its test resources:

```powershell
docker compose config --quiet
python scripts/container_smoke.py

# Repeat the offline search with the 2-CPU/1-GiB override and two Core workers.
python scripts/container_smoke.py --skip-build --resource-limits
```

These containers are scoped to local use and are not published, so third-party image vulnerability scanning is not a mandatory phase gate. Dependencies remain locked and audited, and reviewed base manifests are pinned by full tag and digest in each Dockerfile. On 2026-08-19, clean local amd64 builds measured:

| Image | Docker stored size | Root filesystem | Runtime user |
| --- | ---: | ---: | --- |
| `tlefinder-api` | 199.89 MiB | 220.84 MiB | `tlefinder` (UID/GID 10001) |
| `tlefinder-gui` | 45.90 MiB | 49.53 MiB | `nginx` (unprivileged image user) |

The API image contains the installed API and Core wheels and their runtime dependencies, but no GUI/Node tree, Poetry, test runner, source cache, or compiler. The GUI image contains only reviewed Nginx configuration and fingerprinted static output, with no source maps, `node_modules`, Python environment, API source, npm credentials, or test files.

## Troubleshooting

- Occupied port: set `TLEFINDER_GUI_PORT` (or `TLEFINDER_API_PORT` for the optional override), then recreate the stack.
- Unhealthy service: run `docker compose ps` and `docker compose logs api gui`; API must become healthy before Compose starts GUI.
- Proxy `502`: confirm API is healthy, then recreate GUI with `docker compose up --detach --force-recreate gui` so Nginx resolves the current API container.
- Station permission error: confirm the service uses the named volume at `/data`, not a host bind mount. Inspect with `docker compose config` and recreate the volume only after backup.
- TLE cache permission error: confirm the `tle-cache` named volume is mounted at `/tle-cache` and the API image is current. Do not replace it with a root-owned host directory.
- Stale image: run `docker compose build --pull --no-cache <api|gui>` followed by `docker compose up --detach --wait`.
- Lockfile or missing-file build error: update and commit the owning lockfile from its component directory; do not install an unlocked package in the Dockerfile.
- Read-only filesystem error: station persistence belongs in `/data`, TLE persistence belongs in `/tle-cache`, and other transient runtime files belong in `/tmp`. Do not make the root filesystem writable to hide an incorrect path.
