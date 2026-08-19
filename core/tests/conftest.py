from __future__ import annotations

from datetime import datetime, timezone

import pytest


def pytest_collection_modifyitems(items):
    """Tag every Core test by its owning suite directory."""
    for item in items:
        marker = "functional" if "functional" in item.path.parts else "unit"
        item.add_marker(getattr(pytest.mark, marker))


@pytest.fixture
def station_factory():
    def build_station(**overrides):
        from tlefinder.core.models import GroundStation

        values = {
            "latitude": 48.8566,
            "longitude": 2.3522,
            "elevation_m": 35.0,
        }
        values.update(overrides)
        return GroundStation(**values)

    return build_station


@pytest.fixture
def search_window_factory():
    def build_search_window(**overrides):
        from tlefinder.core.models import SearchWindow

        values = {
            "start_at": datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
            "duration_minutes": 10,
        }
        values.update(overrides)
        return SearchWindow(**values)

    return build_search_window


@pytest.fixture
def search_criteria_factory():
    def build_search_criteria(**overrides):
        from tlefinder.core.models import SearchCriteria

        values = {
            "result_limit": 5,
            "score_threshold": 0.0,
        }
        values.update(overrides)
        return SearchCriteria(**values)

    return build_search_criteria
