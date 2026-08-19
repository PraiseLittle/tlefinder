"""Uvicorn process launcher with environment-driven container settings."""

from __future__ import annotations

from dataclasses import dataclass
import os

import uvicorn


UVICORN_HOST_ENV = "TLEFINDER_UVICORN_HOST"
UVICORN_PORT_ENV = "TLEFINDER_UVICORN_PORT"
UVICORN_WORKERS_ENV = "TLEFINDER_UVICORN_WORKERS"
LOG_LEVEL_ENV = "TLEFINDER_LOG_LEVEL"


@dataclass(frozen=True, slots=True)
class ServerSettings:
    """Resolved Uvicorn process policy."""

    host: str = "127.0.0.1"
    port: int = 2626
    workers: int = 1
    log_level: str = "info"


def resolve_server_settings() -> ServerSettings:
    """Resolve server settings while retaining loopback-only local defaults."""
    return ServerSettings(
        host=os.environ.get(UVICORN_HOST_ENV, "127.0.0.1"),
        port=int(os.environ.get(UVICORN_PORT_ENV, "2626")),
        workers=int(os.environ.get(UVICORN_WORKERS_ENV, "1")),
        log_level=os.environ.get(LOG_LEVEL_ENV, "info"),
    )


def run_server(settings: ServerSettings | None = None) -> None:
    """Run Uvicorn in the foreground so it receives termination signals."""
    resolved = settings or resolve_server_settings()
    uvicorn.run(
        "tlefinder.api.app:app",
        host=resolved.host,
        port=resolved.port,
        workers=resolved.workers,
        log_level=resolved.log_level,
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover - exercised as the container process
    run_server()


__all__ = [
    "LOG_LEVEL_ENV",
    "ServerSettings",
    "UVICORN_HOST_ENV",
    "UVICORN_PORT_ENV",
    "UVICORN_WORKERS_ENV",
    "resolve_server_settings",
    "run_server",
]
