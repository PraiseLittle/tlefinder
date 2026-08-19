from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest


def test_utc_input_stays_utc(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    start = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    normalized = normalize_start_time_to_utc(search_window_factory(start_at=start))

    assert normalized == start
    assert normalized.tzinfo is timezone.utc


def test_fixed_offset_local_time_normalizes_to_utc(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    local_start = datetime(
        2026,
        5,
        12,
        21,
        0,
        tzinfo=timezone(timedelta(hours=1)),
    )
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
        start_at=datetime(
            2026,
            5,
            12,
            21,
            0,
            tzinfo=timezone(timedelta(hours=1)),
        ),
        duration_minutes=15,
    )

    assert build_search_interval(local_window) == build_search_interval(utc_window)


def test_timezone_name_datetime_is_not_normalized(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    window = search_window_factory(
        start_at=datetime(2026, 5, 12, 22, 0, tzinfo=ZoneInfo("Europe/Paris"))
    )

    with pytest.raises(ValueError, match="fixed UTC offset"):
        normalize_start_time_to_utc(window)


def test_naive_datetime_is_not_normalized(search_window_factory):
    from tlefinder.core.time_utils import normalize_start_time_to_utc

    window = search_window_factory(start_at=datetime(2026, 5, 12, 20, 0))

    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_start_time_to_utc(window)


def test_search_interval_adds_duration_minutes(search_window_factory):
    from tlefinder.core.time_utils import build_search_interval

    window = search_window_factory(duration_minutes=12)
    start, end = build_search_interval(window)

    assert end - start == timedelta(minutes=12)


def test_interval_builder_does_not_accept_station_data(search_window_factory):
    from tlefinder.core.time_utils import build_search_interval

    window = search_window_factory(
        start_at=datetime(
            2026,
            5,
            12,
            21,
            0,
            tzinfo=timezone(timedelta(hours=1)),
        ),
        duration_minutes=15,
    )

    with pytest.raises(TypeError):
        build_search_interval(window, object())
