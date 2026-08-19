from __future__ import annotations

import ast
import builtins
from contextlib import contextmanager
import importlib
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPOSITORY_ROOT / "core"
CORE_SOURCE = CORE_ROOT / "src" / "tlefinder"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


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


def test_core_imports_only_core_or_runtime_dependencies():
    forbidden = (
        "tlefinder.api",
        "tlefinder.gui",
        "fastapi",
        "pydantic",
        "yaml",
        "react",
        "vite",
    )
    violations: dict[str, list[str]] = {}
    for path in sorted(CORE_SOURCE.rglob("*.py")):
        bad = sorted(
            module
            for module in imported_modules(path)
            if module in forbidden
            or module.startswith(tuple(f"{item}." for item in forbidden))
        )
        if bad:
            violations[str(path.relative_to(CORE_ROOT))] = bad
    assert violations == {}


def test_core_package_imports_without_api_or_api_dependencies(monkeypatch):
    real_import = builtins.__import__
    blocked_prefixes = ("fastapi", "pydantic", "yaml", "tlefinder.api", "tlefinder.gui")

    def guarded_import(name, *args, **kwargs):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in blocked_prefixes):
            raise AssertionError(f"tlefinder.core must not import {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with temporarily_unimported("tlefinder.core"):
        core = importlib.import_module("tlefinder.core")
    assert core.__name__ == "tlefinder.core"


def test_core_uses_the_shared_implicit_tlefinder_namespace():
    assert not (CORE_SOURCE / "__init__.py").exists()
    assert (CORE_SOURCE / "core" / "__init__.py").is_file()
    assert (CORE_SOURCE / "benchmarks" / "__init__.py").is_file()


def test_repository_has_no_nested_git_directories_or_combined_project_paths():
    nested_git = [
        path
        for path in REPOSITORY_ROOT.rglob(".git")
        if path.resolve() != (REPOSITORY_ROOT / ".git").resolve()
        and "node_modules" not in path.parts
    ]
    assert nested_git == []

    obsolete_paths = [
        REPOSITORY_ROOT / "tlefinder" / "src" / "tlefinder" / "core",
        REPOSITORY_ROOT / "tlefinder" / "src" / "tlefinder" / "api",
        REPOSITORY_ROOT / "tlefinder" / "src" / "tlefinder" / "gui",
        REPOSITORY_ROOT / "tlefinder" / "tests",
        REPOSITORY_ROOT / "tlefinder" / "pyproject.toml",
    ]
    assert [str(path) for path in obsolete_paths if path.exists()] == []
