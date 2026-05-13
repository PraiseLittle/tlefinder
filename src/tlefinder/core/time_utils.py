"""Timezone normalization helpers for search windows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tlefinder.core.models import SearchWindow


def normalize_start_time_to_utc(window: SearchWindow) -> datetime:
    """Return ``window.start_at`` as a timezone-aware UTC datetime."""

    start_at = window.start_at
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("SearchWindow.start_at must be timezone-aware")
    return start_at.astimezone(timezone.utc)


def build_search_interval(window: SearchWindow) -> tuple[datetime, datetime]:
    """Return the normalized inclusive start and exclusive end of a search."""

    start_utc = normalize_start_time_to_utc(window)
    end_utc = start_utc + timedelta(minutes=window.duration_minutes)
    return start_utc, end_utc


__all__ = [
    "build_search_interval",
    "normalize_start_time_to_utc",
]
