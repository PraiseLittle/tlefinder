# HTTP API

## Addresses

For local development:

- API: <http://127.0.0.1:2626>
- Swagger UI: <http://127.0.0.1:2626/docs>
- OpenAPI document: <http://127.0.0.1:2626/openapi.json>
- Health check: <http://127.0.0.1:2626/healthz>
- Versioned API base: \`http://127.0.0.1:2626/api/v1\`

The default Docker Compose configuration exposes only the GUI. Add \`compose.api-port.yaml\` to expose the API on the host.

## Stations

A persisted station has a non-empty name, latitude from -90 to 90 degrees, longitude from -180 to 180 degrees, and elevation from -500 to 8000 metres.

Get the complete list:

~~~powershell
Invoke-RestMethod http://127.0.0.1:2626/api/v1/stations
~~~

Replace the complete list:

~~~powershell
$stations = @{
    stations = @(
        @{
            name = "Paris Observatory"
            latitude = 48.8367
            longitude = 2.3365
            elevation_m = 67
        }
    )
} | ConvertTo-Json -Depth 4

$request = @{
    Method = "Put"
    Uri = "http://127.0.0.1:2626/api/v1/stations"
    ContentType = "application/json"
    Body = $stations
}
Invoke-RestMethod @request
~~~

\`PUT /stations\` replaces the list rather than patching it. Names and physical coordinates must be unique. A successful search also saves its station when the request includes a new name.

## Simple search

Simple search accepts a station, a time window, and an optional \`24h\` or \`1w\` TLE age. It searches the active group with standard broad geometry and metric ranges, no score threshold, and at most 10 results.

~~~powershell
$start = (Get-Date).ToUniversalTime().AddMinutes(5).ToString(
    "yyyy-MM-dd'T'HH:mm:ss'Z'"
)

$simple = @{
    station = @{
        name = "Paris Observatory"
        latitude = 48.8367
        longitude = 2.3365
        elevation_m = 67
    }
    window = @{
        start_at = $start
        duration_minutes = 15
    }
    tle_age_limit = "24h"
} | ConvertTo-Json -Depth 5

$request = @{
    Method = "Post"
    Uri = "http://127.0.0.1:2626/api/v1/search/simple"
    ContentType = "application/json"
    Body = $simple
}
Invoke-RestMethod @request
~~~

## Advanced search

Advanced search additionally accepts:

- Satellite group: \`active\`, \`visual\`, or \`amateur\`.
- Culmination-altitude range or target and tolerance.
- Start, culmination, and end azimuth targets and tolerances.
- Sun-proximity range.
- Satellite-altitude range.
- Positive result limit and score threshold from 0 through 100.

Every criterion is optional. An omitted result limit defaults to 10 and an omitted score threshold defaults to zero.

~~~powershell
$start = (Get-Date).ToUniversalTime().AddMinutes(5).ToString(
    "yyyy-MM-dd'T'HH:mm:ss'Z'"
)

$advanced = @{
    station = @{
        name = "Paris Observatory"
        latitude = 48.8367
        longitude = 2.3365
        elevation_m = 67
    }
    window = @{
        start_at = $start
        duration_minutes = 15
    }
    satellite_group = "active"
    tle_age_limit = "1w"
    criteria = @{
        culmination_altitude_deg = @{
            minimum = 20
            maximum = 80
        }
        start_azimuth_deg = @{
            target = 270
            tolerance = 20
        }
        sun_proximity_deg = @{
            minimum = 30
            maximum = 180
        }
        satellite_altitude_km = @{
            minimum = 400
            maximum = 1200
        }
        result_limit = 5
        score_threshold = 60
    }
} | ConvertTo-Json -Depth 7

$request = @{
    Method = "Post"
    Uri = "http://127.0.0.1:2626/api/v1/search/advanced"
    ContentType = "application/json"
    Body = $advanced
}
Invoke-RestMethod @request
~~~

## Search responses

A successful search returns:

- \`status\`: \`results\` or \`no_result\`.
- \`results\`: ranked candidate passes; empty only for \`no_result\`.
- \`diagnostics\`: counts, timings, TLE information, and optimization details.

Each candidate includes \`satellite\`, \`geometry\`, \`metrics\`, \`match_score\`, \`rank\`, and candidate diagnostics. All response timestamps are ISO 8601 UTC values ending in \`Z\`.

## Errors

All expected failures use:

| Field | Meaning |
| --- | --- |
| \`error.code\` | Stable machine-readable category |
| \`error.message\` | Human-readable summary |
| \`error.details\` | Additional JSON-safe context |
| \`error.field_errors\` | Field and message pairs for validation failures |

Current codes are \`validation_error\`, \`station_validation_error\`, \`station_store_error\`, \`tle_unavailable\`, \`tle_stale\`, \`search_execution_error\`, and \`internal_error\`.

## Runtime configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| \`TLEFINDER_STATION_STORE_PATH\` | Package data directory | YAML station file |
| \`TLEFINDER_TLE_CACHE_DIR\` | \`~/.cache/tlefinder/tle\` | Downloaded TLE cache |
| \`TLEFINDER_PARALLEL_SEARCH_ENABLED\` | \`false\` | Enable process-pool geometry search |
| \`TLEFINDER_PARALLEL_WORKER_COUNT\` | \`4\` | Requested worker count |
| \`TLEFINDER_PARALLEL_CHUNK_SIZE\` | \`32\` | Satellite records per work chunk |
| \`TLEFINDER_UVICORN_HOST\` | \`127.0.0.1\` | Server bind address |
| \`TLEFINDER_UVICORN_PORT\` | \`2626\` | Server port |
| \`TLEFINDER_UVICORN_WORKERS\` | \`1\` | Uvicorn worker processes |
| \`TLEFINDER_LOG_LEVEL\` | \`info\` | Uvicorn log level |

The Compose service overrides storage paths, binds the server to \`0.0.0.0\` inside the container, and stores stations and TLE files in separate named volumes.
