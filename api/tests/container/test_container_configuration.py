from __future__ import annotations

from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def _compose() -> dict:
    return yaml.safe_load(_read("compose.yaml"))


def test_api_dockerfile_is_a_locked_multistage_non_root_runtime():
    dockerfile = _read("api/Dockerfile")

    assert dockerfile.count("FROM ") >= 2
    assert "python:3.12.10-slim-bookworm" in dockerfile
    assert "poetry==2.3.4" in dockerfile
    assert "api/poetry.lock" in dockerfile
    assert "core/poetry.lock" in dockerfile
    assert "poetry install --only main" in dockerfile
    assert "USER tlefinder" in dockerfile
    assert "EXPOSE 2626" in dockerfile
    assert 'CMD ["python", "-m", "tlefinder.api.server"]' in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/healthz" in dockerfile
    assert "/tle-cache" in dockerfile

    runtime = dockerfile.split("FROM ")[-1]
    for forbidden in ("poetry", "gcc", "build-essential", "COPY gui", "COPY .git"):
        assert forbidden not in runtime


def test_api_runtime_dependency_set_does_not_install_reload_or_websocket_extras():
    manifest = _read("api/pyproject.toml")

    assert 'uvicorn = ">=0.30,<1.0"' in manifest
    assert 'extras = ["standard"]' not in manifest


def test_gui_dockerfile_tests_and_builds_from_the_lock_before_minimal_runtime():
    dockerfile = _read("gui/Dockerfile")

    assert dockerfile.count("FROM ") >= 2
    assert "node:22.14.0-alpine3.21" in dockerfile
    assert "nginxinc/nginx-unprivileged:1.27.4-alpine3.21" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm audit --audit-level=high" in dockerfile
    assert "npm test" in dockerfile
    assert "npm run typecheck" in dockerfile
    assert "npm run build" in dockerfile
    assert "USER nginx" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "HEALTHCHECK" in dockerfile

    runtime = dockerfile.split("FROM ")[-1]
    assert "COPY --from=build /build/gui/dist" in runtime
    for forbidden in ("node_modules", "api/src", "core/src", "python", "npm ci"):
        assert forbidden not in runtime


def test_proxy_preserves_api_paths_and_statuses_and_sets_forwarding_headers():
    nginx = _read("gui/nginx.conf")

    assert "location /api/" in nginx
    assert "proxy_pass http://api:2626;" in nginx
    assert "proxy_intercept_errors off;" in nginx
    assert "proxy_set_header Host $host;" in nginx
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in nginx
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in nginx
    assert "location = /healthz" in nginx
    assert "location = /openapi.json" in nginx

    # A proxy_pass without a trailing URI preserves /api/v1 paths and queries.
    assert "proxy_pass http://api:2626/;" not in nginx
    assert "rewrite " not in nginx


def test_proxy_has_spa_fallback_without_masking_missing_static_assets():
    nginx = _read("gui/nginx.conf")

    assert "try_files $uri $uri/ /index.html;" in nginx
    assert "location /assets/" in nginx
    assert "try_files $uri =404;" in nginx
    assert "location ~*" in nginx
    assert "Cache-Control \"no-store\"" in nginx
    assert "immutable" in nginx


def test_compose_connects_healthy_api_to_gui_and_persists_application_data():
    compose = _compose()
    services = compose["services"]

    assert set(services) == {"api", "gui"}
    assert services["api"]["build"] == {
        "context": ".",
        "dockerfile": "api/Dockerfile",
        "target": "runtime",
    }
    assert services["gui"]["build"] == {
        "context": ".",
        "dockerfile": "gui/Dockerfile",
        "target": "runtime",
    }
    assert services["api"]["expose"] == [2626]
    assert "ports" not in services["api"]
    assert services["gui"]["ports"] == ["${TLEFINDER_GUI_PORT:-2627}:8080"]
    assert services["api"]["environment"]["TLEFINDER_UVICORN_HOST"] == "0.0.0.0"
    assert (
        services["api"]["environment"]["TLEFINDER_STATION_STORE_PATH"]
        == "/data/stations.yaml"
    )
    assert services["api"]["environment"]["TLEFINDER_TLE_CACHE_DIR"] == "/tle-cache"
    assert services["api"]["volumes"] == [
        "station-data:/data",
        "tle-cache:/tle-cache",
    ]
    assert services["gui"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert services["api"]["healthcheck"]
    assert services["gui"]["healthcheck"]
    assert services["api"]["networks"] == ["application"]
    assert services["gui"]["networks"] == ["application"]
    assert set(compose["volumes"]) == {"station-data", "tle-cache"}
    assert set(compose["networks"]) == {"application"}


def test_compose_hardens_both_runtimes_and_allows_only_explicit_temp_storage():
    services = _compose()["services"]

    for service in services.values():
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["restart"] == "unless-stopped"
        assert service["stop_grace_period"]
        assert service["tmpfs"]
        assert not any(str(volume).startswith("./") for volume in service.get("volumes", []))


def test_direct_api_publication_is_an_explicit_loopback_only_override():
    override = yaml.safe_load(_read("compose.api-port.yaml"))

    assert override == {
        "services": {
            "api": {
                "ports": ["127.0.0.1:${TLEFINDER_API_PORT:-2626}:2626"]
            }
        }
    }


def test_resource_override_pairs_one_uvicorn_worker_with_two_core_workers():
    override = yaml.safe_load(_read("compose.resources.yaml"))
    api = override["services"]["api"]

    assert api["environment"] == {
        "TLEFINDER_UVICORN_WORKERS": 1,
        "TLEFINDER_PARALLEL_SEARCH_ENABLED": True,
        "TLEFINDER_PARALLEL_WORKER_COUNT": 2,
    }
    assert api["deploy"]["resources"]["limits"] == {
        "cpus": "2.0",
        "memory": "1G",
    }


def test_dockerignore_files_exclude_sources_of_secrets_and_build_noise():
    api_ignore = _read("api/.dockerignore")
    gui_ignore = _read("gui/.dockerignore")

    for pattern in (
        "**/__pycache__/",
        "**/.pytest_cache/",
        "**/.venv/",
        "**/.env*",
        "**/.git/",
        "gui/",
        "**/stations.yaml",
    ):
        assert pattern in api_ignore

    for pattern in (
        "**/node_modules/",
        "**/dist/",
        "**/.env*",
        "**/.git/",
        "api/",
        "core/",
        "**/coverage/",
    ):
        assert pattern in gui_ignore


def test_component_ci_builds_and_smoke_tests_images_without_publishing():
    api_workflow = _read(".github/workflows/api.yml")
    gui_workflow = _read(".github/workflows/gui.yml")
    core_workflow = _read(".github/workflows/core.yml")

    assert "docker build" in api_workflow
    assert "scripts/container_smoke.py" in api_workflow
    assert "docker compose config --quiet" in api_workflow
    assert "push: false" in api_workflow
    assert "docker build" in gui_workflow
    assert "npm audit --audit-level=high" in gui_workflow
    assert "push: false" in gui_workflow
    assert "docker build" not in core_workflow
    assert "tlefinder-core" not in core_workflow


def test_container_smoke_verifies_tle_cache_after_api_recreation():
    smoke_script = _read("scripts/container_smoke.py")

    assert "TLE_CACHE_PATH = \"/tle-cache/active.tle\"" in smoke_script
    assert "TLE cache volume did not survive API container recreation" in smoke_script
