from __future__ import annotations

import builtins
import importlib
import sys
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temporarily_unimported(*module_prefixes: str):
    previous_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in module_prefixes)
    }

    for name in previous_modules:
        sys.modules.pop(name, None)

    try:
        yield
    finally:
        for name in list(sys.modules):
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in module_prefixes):
                sys.modules.pop(name, None)
        sys.modules.update(previous_modules)


def test_api_package_imports_without_gui_modules(monkeypatch):
    real_import = builtins.__import__
    blocked_prefixes = (
        "flask",
        "PySide6",
        "tkinter",
        "tlefinder.gui",
    )

    def guarded_import(name, *args, **kwargs):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in blocked_prefixes):
            raise AssertionError(f"tlefinder.api must not import GUI module {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with temporarily_unimported("tlefinder.api"):
        api = importlib.import_module("tlefinder.api")

    assert api.__name__ == "tlefinder.api"


def test_core_package_imports_without_api_or_api_dependencies(monkeypatch):
    real_import = builtins.__import__
    blocked_prefixes = (
        "fastapi",
        "pydantic",
        "yaml",
        "tlefinder.api",
    )

    def guarded_import(name, *args, **kwargs):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in blocked_prefixes):
            raise AssertionError(f"tlefinder.core must not import {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with temporarily_unimported("tlefinder.core"):
        core = importlib.import_module("tlefinder.core")

    assert core.__name__ == "tlefinder.core"


def test_create_app_returns_fastapi_application_with_metadata_and_api_prefix():
    from fastapi import FastAPI
    from tlefinder.api.app import API_V1_PREFIX, create_app

    app = create_app()

    assert isinstance(app, FastAPI)
    assert app.title == "TLE Finder API"
    assert app.version == "1.0.0"
    assert API_V1_PREFIX == "/api/v1"
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/"):
            assert path.startswith(f"{API_V1_PREFIX}/")


def test_create_app_attaches_custom_api_settings_to_state(tmp_path):
    from tlefinder.api.app import create_app
    from tlefinder.api.config import ApiSettings

    settings = ApiSettings(station_store_path=tmp_path / "stations.yaml")

    app = create_app(settings)

    assert app.state.api_settings is settings


def test_default_settings_use_backend_controlled_station_store_path(monkeypatch):
    from tlefinder.api.config import resolve_api_settings

    monkeypatch.delenv("TLEFINDER_STATION_STORE_PATH", raising=False)

    settings = resolve_api_settings()

    assert settings.station_store_path.name == "stations.yaml"
    assert settings.station_store_path.parent.name == "data"
    assert "core" not in settings.station_store_path.parts


def test_environment_can_override_station_store_path(monkeypatch, tmp_path):
    from tlefinder.api.config import resolve_api_settings

    configured_path = tmp_path / "custom-stations.yaml"
    monkeypatch.setenv("TLEFINDER_STATION_STORE_PATH", str(configured_path))

    settings = resolve_api_settings()

    assert settings.station_store_path == configured_path
