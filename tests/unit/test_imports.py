from __future__ import annotations

import builtins
import importlib


def test_tlefinder_package_imports():
    package = importlib.import_module("tlefinder")

    assert package.__name__ == "tlefinder"


def test_core_package_imports_without_flask(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "flask" or name.startswith("flask."):
            raise AssertionError("tlefinder.core must not import Flask")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    core = importlib.import_module("tlefinder.core")

    assert core.__name__ == "tlefinder.core"

