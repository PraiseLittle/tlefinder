from __future__ import annotations

import ast
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[2]
API_SOURCE = API_ROOT / "src" / "tlefinder"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_api_uses_core_as_a_declared_dependency_and_never_imports_gui():
    imports = {
        module
        for path in API_SOURCE.rglob("*.py")
        for module in imported_modules(path)
    }
    assert any(
        module == "tlefinder.core" or module.startswith("tlefinder.core.")
        for module in imports
    )
    assert not any(
        module == "tlefinder.gui" or module.startswith("tlefinder.gui.")
        for module in imports
    )
    manifest = (API_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'tlefinder-core = { path = "../core", develop = true }' in manifest


def test_api_uses_the_shared_implicit_tlefinder_namespace():
    assert not (API_SOURCE / "__init__.py").exists()
    assert (API_SOURCE / "api" / "__init__.py").is_file()

