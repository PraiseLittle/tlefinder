#!/usr/bin/env python3
"""Build-time and runtime smoke tests for the Phase 23 container contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "tlefinder-phase23-smoke"
API_IMAGE = "tlefinder-api:phase23-smoke"
GUI_IMAGE = "tlefinder-gui:phase23-smoke"
GUI_PORT = 3627
BASE_URL = f"http://127.0.0.1:{GUI_PORT}"
TLE_CACHE_PATH = "/tle-cache/active.tle"


class SmokeFailure(RuntimeError):
    """Raised when a container contract assertion fails."""


def run(*arguments: str, capture: bool = False) -> str:
    completed = subprocess.run(
        arguments,
        cwd=REPOSITORY_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    return completed.stdout if capture else ""


def compose(*arguments: str, capture: bool = False) -> str:
    return run("docker", "compose", "-p", PROJECT_NAME, *arguments, capture=capture)


def request(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> tuple[int, bytes, dict[str, str]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    http_request = Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with urlopen(http_request, timeout=10) as response:
            status = response.status
            response_body = response.read()
            response_headers = dict(response.headers.items())
    except HTTPError as exc:
        status = exc.code
        response_body = exc.read()
        response_headers = dict(exc.headers.items())
    except URLError as exc:
        raise SmokeFailure(f"request failed for {path}: {exc}") from exc
    if status != expected_status:
        raise SmokeFailure(
            f"{method} {path} returned {status}, expected {expected_status}: "
            f"{response_body.decode('utf-8', errors='replace')}"
        )
    return status, response_body, response_headers


def wait_for_stack(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            request("/")
            request("/healthz")
            return
        except (SmokeFailure, OSError) as exc:
            last_error = exc
            time.sleep(2)
    raise SmokeFailure(f"stack did not become healthy within {timeout_seconds}s: {last_error}")


def assert_image_contents() -> None:
    api_probe = run(
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "python",
        API_IMAGE,
        "-c",
        (
            "import importlib.util, pathlib, tlefinder.api, tlefinder.core; "
            "assert importlib.util.find_spec('node') is None; "
            "assert importlib.util.find_spec('poetry') is None; "
            "assert importlib.util.find_spec('pytest') is None; "
            "root=pathlib.Path('/app'); "
            "assert not (root/'gui').exists(); "
            "venv=pathlib.Path('/opt/venv'); "
            "assert not list(venv.rglob('.pytest_cache')); "
            "assert not list(venv.rglob('node_modules')); "
            "assert not list(venv.rglob('.git')); "
            "assert not list(venv.rglob('.env*')); "
            "assert not list(venv.rglob('.pypirc')); "
            "assert not list(venv.rglob('.npmrc')); "
            "assert not list(venv.rglob('stations.yaml')); "
            "print(tlefinder.api.__name__, tlefinder.core.__name__)"
        ),
        capture=True,
    )
    if "tlefinder.api tlefinder.core" not in api_probe:
        raise SmokeFailure("API image does not import the installed API and Core packages")

    gui_probe = run(
        "docker",
        "run",
        "--rm",
        "--entrypoint",
        "/bin/sh",
        GUI_IMAGE,
        "-c",
        (
            "test -f /usr/share/nginx/html/index.html && "
            "test -n \"$(find /usr/share/nginx/html/assets -type f -name '*.js' -print -quit)\" && "
            "! find /usr/share/nginx/html -type f -name '*.map' -print -quit | grep -q . && "
            "! find / -type d -name node_modules -print -quit 2>/dev/null | grep -q . && "
            "! find / -type d -name .git -print -quit 2>/dev/null | grep -q . && "
            "! find / -type f -name '*.py' -print -quit 2>/dev/null | grep -q . && "
            "! find / -type f \( -name '.env*' -o -name '.npmrc' \) "
            "-print -quit 2>/dev/null | grep -q ."
        ),
        capture=True,
    )
    if gui_probe.strip():
        raise SmokeFailure(f"unexpected GUI image inspection output: {gui_probe}")


def assert_http_contract() -> None:
    _, health_body, _ = request("/healthz")
    if json.loads(health_body) != {"status": "ok"}:
        raise SmokeFailure("proxied health response did not come from the API")

    _, openapi_body, _ = request("/openapi.json")
    paths = json.loads(openapi_body)["paths"]
    expected_operations = {
        ("/api/v1/stations", "get"),
        ("/api/v1/stations", "put"),
        ("/api/v1/search/simple", "post"),
        ("/api/v1/search/advanced", "post"),
    }
    actual_operations = {
        (path, method)
        for path, operations in paths.items()
        for method in operations
        if method in {"get", "put", "post", "delete", "patch"}
    }
    if not expected_operations.issubset(actual_operations):
        raise SmokeFailure("OpenAPI lost one or more public /api/v1 operations")

    _, spa_body, spa_headers = request("/search/history")
    if b'<div id="root"></div>' not in spa_body:
        raise SmokeFailure("non-root GUI route did not receive the SPA document")
    if "text/html" not in spa_headers.get("Content-Type", ""):
        raise SmokeFailure("SPA fallback did not return HTML")

    request("/assets/definitely-missing.js", expected_status=404)
    _, missing_api_body, _ = request("/api/v1/definitely-missing", expected_status=404)
    if json.loads(missing_api_body).get("detail") != "Not Found":
        raise SmokeFailure("proxy masked the API 404 response body")


def assert_persistence_contract() -> None:
    station = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    request(
        "/api/v1/stations",
        method="PUT",
        payload={"stations": [station]},
    )

    invalid_station = dict(station, name="")
    request(
        "/api/v1/stations",
        method="PUT",
        payload={"stations": [invalid_station]},
        expected_status=422,
    )
    _, body_after_invalid_update, _ = request("/api/v1/stations")
    if json.loads(body_after_invalid_update) != {"stations": [station]}:
        raise SmokeFailure("invalid station update changed the persisted station list")

    compose("up", "-d", "--no-deps", "--force-recreate", "api")
    wait_for_stack()
    _, body_after_recreate, _ = request("/api/v1/stations")
    if json.loads(body_after_recreate) != {"stations": [station]}:
        raise SmokeFailure("station volume did not survive API container recreation")


def assert_fixture_backed_search() -> None:
    fixture = REPOSITORY_ROOT / "core" / "tests" / "fixtures" / "active_sample.tle"
    subprocess.run(
        (
            "docker",
            "compose",
            "-p",
            PROJECT_NAME,
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            (
                "import pathlib, sys; "
                f"path=pathlib.Path({TLE_CACHE_PATH!r}); "
                "path.parent.mkdir(parents=True, exist_ok=True); "
                "path.write_bytes(sys.stdin.buffer.read())"
            ),
        ),
        cwd=REPOSITORY_ROOT,
        input=fixture.read_bytes(),
        check=True,
    )

    payload = {
        "station": {
            "latitude": 48.8367,
            "longitude": 2.3365,
            "elevation_m": 67.0,
        },
        "window": {
            "start_at": "2026-05-12T14:50:00Z",
            "duration_minutes": 12,
        },
        "tle_age_limit": "24h",
    }
    _, body, _ = request("/api/v1/search/simple", method="POST", payload=payload)
    parsed = json.loads(body)
    if parsed.get("status") not in {"results", "no_result"}:
        raise SmokeFailure("fixture-backed search did not return a valid search response")
    if parsed.get("diagnostics", {}).get("satellite_count") != 2:
        raise SmokeFailure("fixture-backed search did not use the two-record local fixture")

    compose("up", "-d", "--no-deps", "--force-recreate", "api")
    wait_for_stack()
    persisted_size = compose(
        "exec",
        "-T",
        "api",
        "python",
        "-c",
        (
            "import pathlib; "
            f"path=pathlib.Path({TLE_CACHE_PATH!r}); "
            "print(path.stat().st_size if path.is_file() else -1)"
        ),
        capture=True,
    ).strip()
    if persisted_size != str(fixture.stat().st_size):
        raise SmokeFailure("TLE cache volume did not survive API container recreation")

    _, body_after_recreate, _ = request(
        "/api/v1/search/simple",
        method="POST",
        payload=payload,
    )
    parsed_after_recreate = json.loads(body_after_recreate)
    if parsed_after_recreate.get("diagnostics", {}).get("satellite_count") != 2:
        raise SmokeFailure("recreated API did not reuse the persisted TLE fixture")


def assert_stack_stopped() -> None:
    running_ids = compose("ps", "-q", capture=True).strip()
    if running_ids:
        raise SmokeFailure(f"application containers remain running: {running_ids}")


def assert_resource_limits() -> None:
    api_container_id = compose("ps", "-q", "api", capture=True).strip()
    if not api_container_id:
        raise SmokeFailure("could not resolve the API container for limit inspection")
    limits = run(
        "docker",
        "inspect",
        "--format",
        "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}",
        api_container_id,
        capture=True,
    ).strip()
    if limits != "2000000000 1073741824":
        raise SmokeFailure(f"unexpected API CPU/memory limits: {limits}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="reuse images already tagged for the smoke test",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the test stack and named volume after a failure",
    )
    parser.add_argument(
        "--resource-limits",
        action="store_true",
        help="apply compose.resources.yaml and verify its CPU/memory policy",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    environment = os.environ.copy()
    environment.update(
        {
            "TLEFINDER_GUI_PORT": str(GUI_PORT),
            "TLEFINDER_API_IMAGE": API_IMAGE,
            "TLEFINDER_GUI_IMAGE": GUI_IMAGE,
        }
    )
    os.environ.update(environment)
    if args.resource_limits:
        os.environ["COMPOSE_FILE"] = os.pathsep.join(
            ("compose.yaml", "compose.resources.yaml")
        )

    compose("down", "--volumes", "--remove-orphans")
    try:
        if not args.skip_build:
            compose("build", "--no-cache")
        assert_image_contents()
        compose("up", "-d")
        wait_for_stack()
        if args.resource_limits:
            assert_resource_limits()
        assert_http_contract()
        assert_persistence_contract()
        assert_fixture_backed_search()
    except Exception:
        try:
            compose("ps")
            compose("logs", "--no-color")
        finally:
            if not args.keep:
                compose("down", "--volumes", "--remove-orphans")
        raise
    compose("down", "--volumes", "--remove-orphans")
    assert_stack_stopped()
    print("Container smoke, proxy, search, and persistence checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeFailure, subprocess.CalledProcessError) as exc:
        print(f"container smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
