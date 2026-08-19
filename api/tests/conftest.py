from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items):
    """Tag every API test by its owning suite directory."""
    for item in items:
        marker = "functional" if "functional" in item.path.parts else "unit"
        item.add_marker(getattr(pytest.mark, marker))

