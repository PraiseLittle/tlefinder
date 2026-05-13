from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def test_utc_input_stays_utc(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    start = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    normalized = normalize_start_time_to_utc(search_window_factory(start_at=start))

    assert normalized == start
    assert normalized.tzinfo is timezone.utc


def test_local_time_with_explicit_timezone_normalizes_to_utc(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    local_start = datetime(2026, 5, 12, 22, 0, tzinfo=ZoneInfo("Europe/Paris"))
    normalized = normalize_start_time_to_utc(
        search_window_factory(start_at=local_start)
    )

    assert normalized == datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)


def test_equivalent_utc_and_local_inputs_build_same_interval(search_window_factory):
    from tlefinder.core.time_utils import build_search_interval

    utc_window = search_window_factory(
        start_at=datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        duration_minutes=15,
    )
    local_window = search_window_factory(
        start_at=datetime(2026, 5, 12, 22, 0, tzinfo=ZoneInfo("Europe/Paris")),
        duration_minutes=15,
    )

    assert build_search_interval(local_window) == build_search_interval(utc_window)


def test_search_interval_adds_duration_minutes(search_window_factory):
    from tlefinder.core.time_utils import build_search_interval

    window = search_window_factory(duration_minutes=12)
    start, end = build_search_interval(window)

    assert end - start == timedelta(minutes=12)
