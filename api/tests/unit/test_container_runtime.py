from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


_SERVER_ENVIRONMENT_VARIABLES = (
    "TLEFINDER_UVICORN_HOST",
    "TLEFINDER_UVICORN_PORT",
    "TLEFINDER_UVICORN_WORKERS",
    "TLEFINDER_LOG_LEVEL",
)


def _clear_server_environment(monkeypatch) -> None:
    for variable_name in _SERVER_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_non_container_server_defaults_remain_loopback_only(monkeypatch):
    from tlefinder.api.server import resolve_server_settings

    _clear_server_environment(monkeypatch)

    settings = resolve_server_settings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 2626
    assert settings.workers == 1
    assert settings.log_level == "info"


def test_container_environment_binds_uvicorn_to_the_container_interface(monkeypatch):
    from tlefinder.api.server import resolve_server_settings

    _clear_server_environment(monkeypatch)
    monkeypatch.setenv("TLEFINDER_UVICORN_HOST", "0.0.0.0")
    monkeypatch.setenv("TLEFINDER_UVICORN_PORT", "2626")
    monkeypatch.setenv("TLEFINDER_UVICORN_WORKERS", "2")
    monkeypatch.setenv("TLEFINDER_LOG_LEVEL", "warning")

    settings = resolve_server_settings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 2626
    assert settings.workers == 2
    assert settings.log_level == "warning"


def test_server_launcher_applies_the_resolved_production_policy(monkeypatch):
    from tlefinder.api import server

    received: list[tuple[tuple, dict]] = []
    settings = server.ServerSettings(
        host="0.0.0.0",
        port=2626,
        workers=2,
        log_level="warning",
    )
    monkeypatch.setattr(
        server.uvicorn,
        "run",
        lambda *args, **kwargs: received.append((args, kwargs)),
    )

    server.run_server(settings)

    assert received == [
        (
            ("tlefinder.api.app:app",),
            {
                "host": "0.0.0.0",
                "port": 2626,
                "workers": 2,
                "log_level": "warning",
                "proxy_headers": True,
                "forwarded_allow_ips": "*",
                "reload": False,
            },
        )
    ]


def test_container_persistence_environment_uses_the_named_volumes(monkeypatch):
    from tlefinder.api.config import resolve_api_settings

    monkeypatch.setenv("TLEFINDER_STATION_STORE_PATH", "/data/stations.yaml")
    monkeypatch.setenv("TLEFINDER_TLE_CACHE_DIR", "/tle-cache")

    settings = resolve_api_settings()

    assert settings.station_store_path == Path("/data/stations.yaml")
    assert settings.tle_cache_dir == Path("/tle-cache")


def test_healthz_is_a_side_effect_free_liveness_route(monkeypatch, tmp_path):
    from tlefinder.api import station_store
    from tlefinder.api.app import create_app
    from tlefinder.api.config import ApiSettings
    from tlefinder.api.routers import search as search_routes

    def forbidden_call(*_args, **_kwargs):
        raise AssertionError("liveness must not access storage, Core, or the network")

    monkeypatch.setattr(station_store, "ensure_store_exists", forbidden_call)
    monkeypatch.setattr(station_store, "load_stations", forbidden_call)
    monkeypatch.setattr(search_routes.core, "search_candidates", forbidden_call)
    station_store_path = tmp_path / "stations.yaml"
    client = TestClient(
        create_app(ApiSettings(station_store_path=station_store_path))
    )

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert not station_store_path.exists()
