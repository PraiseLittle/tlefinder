from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

import pytest


API_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = API_ROOT.parent / "core"
REPOSITORY_ROOT = API_ROOT.parent
POETRY = (
    shutil.which("poetry.bat")
    if os.name == "nt"
    else shutil.which("poetry")
) or "poetry"


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@pytest.fixture(scope="module")
def package_wheels(tmp_path_factory):
    wheel_directory = tmp_path_factory.mktemp("package-wheels")
    projects = {"core": CORE_ROOT, "api": API_ROOT}
    wheels = {}
    for name, project in projects.items():
        subprocess.run(
            [
                POETRY,
                "build",
                "--format",
                "wheel",
                "--output",
                str(wheel_directory),
            ],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        wheels[name] = next(wheel_directory.glob(f"tlefinder_{name}-*.whl"))
    return wheels


@pytest.mark.parametrize(
    "installation_order",
    [("core", "api"), ("api", "core")],
    ids=["core-first", "api-first"],
)
def test_api_and_core_share_the_namespace_in_either_installation_order(
    tmp_path,
    installation_order,
    package_wheels,
):
    environment = tmp_path / "environment"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
    python = _venv_python(environment)
    for package_name in installation_order:
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(package_wheels[package_name]),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    site_packages = subprocess.run(
        [
            str(python),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    script = """
import importlib.metadata
import json
from pathlib import Path
import sys

repository_root = Path(%r).resolve()
source_roots = {
    (repository_root / "core" / "src").resolve(),
    (repository_root / "api" / "src").resolve(),
    (repository_root / "tlefinder" / "src").resolve(),
}
sys.path[:] = [
    item for item in sys.path
    if Path(item or ".").resolve() not in source_roots
]
import tlefinder.api
import tlefinder.api.app
import tlefinder.core

print(json.dumps({
    "api_distribution": importlib.metadata.version("tlefinder-api"),
    "core_distribution": importlib.metadata.version("tlefinder-core"),
    "api_file": tlefinder.api.__file__,
    "core_file": tlefinder.core.__file__,
    "app_title": tlefinder.api.app.app.title,
}))
""" % str(REPOSITORY_ROOT)
    environment_variables = os.environ.copy()
    environment_variables["PYTHONPATH"] = site_packages
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env=environment_variables,
    )
    evidence = json.loads(result.stdout)
    assert evidence["api_distribution"] == "0.1.0"
    assert evidence["core_distribution"] == "0.1.0"
    assert evidence["app_title"] == "TLE Finder API"
    expected_root = str(environment).replace("\\", "/")
    assert expected_root in evidence["api_file"].replace("\\", "/")
    assert expected_root in evidence["core_file"].replace("\\", "/")
