"""Local development launcher for the API and GUI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUI_DIR = PROJECT_ROOT / "src" / "tlefinder" / "gui"


def main() -> int:
    """Start the API first, then the GUI dev server."""
    args = _parse_args()
    api_process: subprocess.Popen[str] | None = None
    gui_process: subprocess.Popen[str] | None = None

    try:
        api_process = _start_api(args)
        api_url = _local_url(args.api_host, args.api_port, "/openapi.json")
        _wait_for_url(api_url, "API", api_process, args.startup_timeout)
        print(f"API ready at {_local_url(args.api_host, args.api_port)}", flush=True)

        if not args.skip_gui_install:
            _install_gui_dependencies_if_needed()

        gui_process = _start_gui(args)
        gui_url = _local_url(args.gui_host, args.gui_port)
        _wait_for_url(gui_url, "GUI", gui_process, args.startup_timeout)
        print(f"GUI ready at {gui_url}", flush=True)
        print("Press Ctrl+C to stop both services.", flush=True)

        while True:
            _raise_if_exited(api_process, "API")
            _raise_if_exited(gui_process, "GUI")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping API and GUI...", flush=True)
        return 0
    except RuntimeError as exc:
        print(f"Failed to start development services: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        _terminate(gui_process)
        _terminate(api_process)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the TLE Finder API and GUI.")
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", default=2626, type=int)
    parser.add_argument(
        "--api-reload",
        action="store_true",
        help="Enable uvicorn reload for the API process.",
    )
    parser.add_argument("--gui-host", default="127.0.0.1")
    parser.add_argument("--gui-port", default=2627, type=int)
    parser.add_argument("--startup-timeout", default=30.0, type=float)
    parser.add_argument(
        "--skip-gui-install",
        action="store_true",
        help="Do not run npm install when GUI dependencies are missing.",
    )
    return parser.parse_args()


def _start_api(args: argparse.Namespace) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "tlefinder.api.app:app",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    if args.api_reload:
        command.append("--reload")

    print("Starting API...", flush=True)
    return subprocess.Popen(command, cwd=PROJECT_ROOT, text=True)


def _start_gui(args: argparse.Namespace) -> subprocess.Popen[str]:
    npm = _find_executable("npm")
    command = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        args.gui_host,
        "--port",
        str(args.gui_port),
    ]
    print("Starting GUI...", flush=True)
    return subprocess.Popen(command, cwd=GUI_DIR, text=True)


def _install_gui_dependencies_if_needed() -> None:
    if (GUI_DIR / "node_modules").exists():
        return

    npm = _find_executable("npm")
    print("Installing GUI dependencies...", flush=True)
    try:
        subprocess.run([npm, "install"], cwd=GUI_DIR, check=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"npm install failed with code {exc.returncode}") from exc


def _wait_for_url(
    url: str,
    process_name: str,
    process: subprocess.Popen[str],
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        _raise_if_exited(process, process_name)
        try:
            with urlopen(url, timeout=1):
                return
        except (HTTPError, OSError, URLError):
            time.sleep(0.25)

    raise RuntimeError(f"{process_name} did not become ready at {url}")


def _raise_if_exited(process: subprocess.Popen[str], process_name: str) -> None:
    return_code = process.poll()
    if return_code is not None:
        raise RuntimeError(f"{process_name} exited with code {return_code}")


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _find_executable(name: str) -> str:
    if sys.platform == "win32":
        executable = shutil.which(f"{name}.cmd") or shutil.which(name)
    else:
        executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"{name} is required but was not found on PATH")
    return executable


def _local_url(host: str, port: int, path: str = "") -> str:
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{url_host}:{port}{path}"


if __name__ == "__main__":
    raise SystemExit(main())
