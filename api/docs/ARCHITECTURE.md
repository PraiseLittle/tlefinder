# API Architecture

## Responsibility

The API is the HTTP and persistence boundary around TLE Finder Core. It owns request validation, schema conversion, station storage, error responses, OpenAPI, and server configuration. It does not implement orbital search logic.

The public Python package is \`tlefinder.api\`. Its only domain dependency is the sibling \`tlefinder-core\` distribution.

## Package layout

| Module | Responsibility |
| --- | --- |
| \`app.py\` | FastAPI application factory, health route, handlers, and routers |
| \`schemas.py\` | Strict Pydantic request, response, station, and error models |
| \`adapters.py\` | Conversion between API schemas and Core dataclasses |
| \`routers/stations.py\` | Read and replace station endpoints |
| \`routers/search.py\` | Simple and advanced search endpoints |
| \`station_store.py\` | YAML loading, validation, uniqueness, and atomic writes |
| \`errors.py\` | Stable API error envelopes and exception handlers |
| \`config.py\` | Search, cache, parallelism, and station-store settings |
| \`server.py\` | Environment-driven Uvicorn launcher |

## Application lifecycle

\`create_app\` resolves \`ApiSettings\`, stores them on \`app.state\`, registers exception handlers, and mounts the station and search routers under \`/api/v1\`. The module-level \`app\` supports Uvicorn and ASGI servers.

\`GET /healthz\` is deliberately lightweight: it reports process liveness without reading storage or contacting the TLE source.

## Request flow

Station requests follow this path:

1. Pydantic rejects unknown fields and invalid coordinate or name values.
2. The station router selects the configured YAML store.
3. \`station_store\` validates the complete collection and physical uniqueness.
4. Replacement data is written through a temporary file and atomically moved into place.
5. The persisted list is returned using the public response schema.

Search requests follow this path:

1. Pydantic validates station coordinates, explicit-offset time, duration, group, TLE age, and criteria.
2. \`adapters.py\` converts the API models into a Core \`SearchRequest\`.
3. The router calls \`tlefinder.core.search_candidates\` with the configured cache and parallel settings.
4. A named station is added to the store after a successful search if it is not already present.
5. Core dataclasses are converted into JSON response models.

The simple endpoint always uses the active group and standard broad criteria with a result limit of 10. It requests Core’s approximate budgeted optimization when that optimization is compatible. The advanced endpoint maps only criteria explicitly sent by the caller and uses exact search behavior.

## Contract and serialization

All public Pydantic models forbid extra fields. Input datetimes must include \`Z\` or an explicit numeric offset. Search-result and TLE timestamps are serialized in UTC with a \`Z\` suffix.

The response keeps Core’s rank order. Each result contains:

- Rank and 0–100 match score.
- Satellite name and NORAD catalog number.
- The exact TLE name, lines, epoch, and source group used.
- Pass geometry and derived metrics.
- JSON-friendly candidate diagnostics.

Top-level diagnostics describe the dataset and search execution. They are useful for observation but are not inputs to a later request.

## Error boundary

Expected exceptions are returned in one envelope:

~~~json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {},
    "field_errors": [
      {
        "field": "window.duration_minutes",
        "message": "Input should be less than or equal to 30"
      }
    ]
  }
}
~~~

Validation errors return 422, unavailable or stale TLE data returns 503, and persistence or execution failures return 500. Unexpected exceptions are logged by FastAPI and returned as a generic internal error without exposing private stack details.

## Tests and packaging

Unit tests cover schemas, adapters, routes, configuration, persistence, errors, and component boundaries. Functional tests exercise HTTP workflows, OpenAPI, operational failures, and wheel packaging. Container tests validate Dockerfiles, Compose, Nginx proxying, health checks, persistence, and CI configuration.

Poetry builds the independent \`tlefinder-api\` distribution and installs \`tlefinder-core\` through its declared sibling path dependency. Both packages share the implicit \`tlefinder\` namespace.
