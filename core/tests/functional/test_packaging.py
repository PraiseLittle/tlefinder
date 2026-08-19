from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

import pytest


CORE_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = CORE_ROOT.parent
POETRY = (
    shutil.which("poetry.bat")
    if os.name == "nt"
    else shutil.which("poetry")
) or "poetry"


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_core_imports_when_only_the_core_distribution_is_installed(tmp_path):
    wheel_directory = tmp_path / "wheel"
    subprocess.run(
        [
            POETRY,
            "build",
            "--format",
            "wheel",
            "--output",
            str(wheel_directory),
        ],
        cwd=CORE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(wheel_directory.glob("tlefinder_core-*.whl"))
    environment = tmp_path / "core-only"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
    python = _venv_python(environment)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(wheel),
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
import importlib.util
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
import tlefinder.core

print(json.dumps({
    "distribution": importlib.metadata.version("tlefinder-core"),
    "core_file": tlefinder.core.__file__,
    "api_spec": importlib.util.find_spec("tlefinder.api"),
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
    assert evidence["distribution"] == "0.1.0"
    assert str(environment).replace("\\", "/") in evidence["core_file"].replace("\\", "/")
    assert evidence["api_spec"] is None


@pytest.mark.parametrize("package", ["tlefinder.api", "fastapi", "pydantic", "yaml"])
def test_core_manifest_does_not_declare_api_owned_dependencies(package):
    manifest = (CORE_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert package not in manifest
