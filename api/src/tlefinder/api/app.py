"""FastAPI application factory for the TLE Finder API."""

from __future__ import annotations

from fastapi import FastAPI

from tlefinder.api.config import ApiSettings, resolve_api_settings
from tlefinder.api.errors import register_exception_handlers
from tlefinder.api.routers import search, stations

API_V1_PREFIX = "/api/v1"


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Create a configured FastAPI application instance."""
    resolved_settings = settings or resolve_api_settings()
    app = FastAPI(
        title="TLE Finder API",
        version="1.0.0",
        description=(
            "HTTP API for TLE Finder search execution and optical ground "
            "station persistence."
        ),
    )
    app.state.api_settings = resolved_settings

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        """Report process liveness without touching storage or the network."""
        return {"status": "ok"}

    register_exception_handlers(app)
    app.include_router(stations.router, prefix=API_V1_PREFIX)
    app.include_router(search.router, prefix=API_V1_PREFIX)

    return app


app = create_app()

__all__ = ["API_V1_PREFIX", "app", "create_app"]
