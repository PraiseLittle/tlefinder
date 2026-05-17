from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
FULL_PASS_INTERVAL = (
    datetime(2026, 5, 12, 14, 50, tzinfo=timezone.utc),
    datetime(2026, 5, 12, 15, 2, tzinfo=timezone.utc),
)
PARTIAL_END_INTERVAL = (
    datetime(2026, 5, 12, 14, 53, tzinfo=timezone.utc),
    datetime(2026, 5, 12, 14, 57, tzinfo=timezone.utc),
)
PARTIAL_START_INTERVAL = (
    datetime(2026, 5, 12, 14, 57, tzinfo=timezone.utc),
    datetime(2026, 5, 12, 15, 1, tzinfo=timezone.utc),
)
OVERLAP_ONLY_INTERVAL = (
    datetime(2026, 5, 12, 14, 57, tzinfo=timezone.utc),
    datetime(2026, 5, 12, 14, 59, tzinfo=timezone.utc),
)
MIDNIGHT_OVERLAP_INTERVAL = (
    datetime(2026, 6, 19, 0, 0, 30, tzinfo=timezone.utc),
    datetime(2026, 6, 19, 0, 1, tzinfo=timezone.utc),
)
PREVIOUS_DAY_RISE_INTERVAL = (
    datetime(2026, 6, 17, 0, 2, tzinfo=timezone.utc),
    datetime(2026, 6, 17, 0, 3, tzinfo=timezone.utc),
)


def _active_satellite_records():
    from tlefinder.core.tle_repository import (
        build_satellite_records,
        parse_tle_file,
    )

    return build_satellite_records(parse_tle_file(FIXTURES_DIR / "active_sample.tle"))


def _iss_record():
    return _active_satellite_records()[0]


def _assert_datetime_close(
    actual: datetime,
    expected: datetime,
    *,
    tolerance_seconds: float = 0.5,
) -> None:
    assert actual.utcoffset() == timedelta(0)
    assert abs((actual - expected).total_seconds()) <= tolerance_seconds


def test_compute_alt_az_and_orbital_altitude_at_known_instant(station_factory):
    from tlefinder.core.pass_analysis import (
        compute_alt_az,
        compute_satellite_altitude_km,
    )

    event_time = datetime(2026, 5, 12, 14, 56, 48, 323001, tzinfo=timezone.utc)

    altitude_deg, azimuth_deg = compute_alt_az(
        _iss_record(),
        station_factory(),
        event_time,
    )
    satellite_altitude_km = compute_satellite_altitude_km(_iss_record(), event_time)

    assert altitude_deg == pytest.approx(67.4088, abs=1e-3)
    assert azimuth_deg == pytest.approx(154.6800, abs=1e-3)
    assert satellite_altitude_km == pytest.approx(418.7069, abs=1e-3)


def test_compute_pass_geometry_extracts_bounded_pass(station_factory):
    from tlefinder.core.pass_analysis import compute_pass_geometry

    geometry = compute_pass_geometry(
        _iss_record(),
        station_factory(),
        FULL_PASS_INTERVAL,
    )

    assert geometry is not None
    _assert_datetime_close(
        geometry.start_time_utc,
        datetime(2026, 5, 12, 14, 53, 29, 627720, tzinfo=timezone.utc),
    )
    _assert_datetime_close(
        geometry.culmination_time_utc,
        datetime(2026, 5, 12, 14, 56, 48, 323001, tzinfo=timezone.utc),
    )
    _assert_datetime_close(
        geometry.end_time_utc,
        datetime(2026, 5, 12, 15, 0, 7, 939541, tzinfo=timezone.utc),
    )
    assert geometry.start_azimuth_deg == pytest.approx(237.4211, abs=1e-3)
    assert geometry.culmination_azimuth_deg == pytest.approx(154.6800, abs=1e-3)
    assert geometry.end_azimuth_deg == pytest.approx(71.9082, abs=1e-3)
    assert geometry.culmination_altitude_deg == pytest.approx(67.4088, abs=1e-3)


def test_compute_pass_geometry_preserves_real_set_for_partial_end_window(
    station_factory,
):
    from tlefinder.core.pass_analysis import compute_pass_geometry

    geometry = compute_pass_geometry(
        _iss_record(),
        station_factory(),
        PARTIAL_END_INTERVAL,
    )

    assert geometry is not None
    assert geometry.end_time_utc > PARTIAL_END_INTERVAL[1]
    _assert_datetime_close(
        geometry.end_time_utc,
        datetime(2026, 5, 12, 15, 0, 7, 939541, tzinfo=timezone.utc),
    )
    assert geometry.end_azimuth_deg == pytest.approx(71.9082, abs=1e-3)


def test_compute_pass_geometry_preserves_real_rise_for_partial_start_window(
    station_factory,
):
    from tlefinder.core.pass_analysis import compute_pass_geometry

    geometry = compute_pass_geometry(
        _iss_record(),
        station_factory(),
        PARTIAL_START_INTERVAL,
    )

    assert geometry is not None
    assert geometry.start_time_utc < PARTIAL_START_INTERVAL[0]
    _assert_datetime_close(
        geometry.start_time_utc,
        datetime(2026, 5, 12, 14, 53, 29, 627720, tzinfo=timezone.utc),
    )
    assert geometry.start_azimuth_deg == pytest.approx(237.4211, abs=1e-3)


def test_compute_pass_metrics_sets_mean_altitude_and_sun_proximity(
    station_factory,
):
    from tlefinder.core.models import CandidatePass, PassMetrics
    from tlefinder.core.pass_analysis import compute_pass_geometry, compute_pass_metrics

    geometry = compute_pass_geometry(
        _iss_record(),
        station_factory(),
        FULL_PASS_INTERVAL,
    )
    candidate = CandidatePass(
        satellite=_iss_record(),
        geometry=geometry,
        metrics=PassMetrics(satellite_altitude_km=0.0),
    )

    metrics = compute_pass_metrics(candidate, station_factory())

    assert metrics.satellite_altitude_km == pytest.approx(418.63, abs=0.05)
    assert metrics.sun_proximity_deg == pytest.approx(18.0, abs=0.5)


def test_find_candidate_passes_returns_candidates_with_metrics_and_diagnostics(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    candidates = find_candidate_passes(
        _active_satellite_records(),
        station_factory(),
        PARTIAL_END_INTERVAL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.satellite.tle.name == "ISS (ZARYA)"
    assert candidate.metrics.satellite_altitude_km == pytest.approx(418.63, abs=0.05)
    assert candidate.metrics.sun_proximity_deg == pytest.approx(18.0, abs=0.5)
    assert candidate.match_score is None
    assert candidate.rank is None
    assert candidate.diagnostics["partial_window"] is True
    assert candidate.diagnostics["start_time_source"] == "observed"
    assert candidate.diagnostics["end_time_source"] == "extended_search"


def test_find_candidate_passes_keeps_architecture_signature():
    import inspect

    from tlefinder.core.pass_analysis import find_candidate_passes

    signature = inspect.signature(find_candidate_passes)

    assert list(signature.parameters) == ["records", "station", "interval"]


def test_internal_candidate_pass_aggregation_preserves_skipped_record_diagnostics(
    station_factory,
):
    from tlefinder.core import pass_analysis

    candidates, skipped_diagnostics = pass_analysis._find_candidate_passes_with_diagnostics(
        _active_satellite_records(),
        station_factory(),
        FULL_PASS_INTERVAL,
    )

    assert [candidate.satellite.tle.name for candidate in candidates] == ["ISS (ZARYA)"]
    assert skipped_diagnostics == [
        {
            "satellite_name": "HST",
            "catalog_number": 20580,
            "event_count": 0,
            "event_sequence": [],
            "partial_window": False,
            "skipped_reason": "no_rise_culmination_pair",
        }
    ]


def test_find_candidate_passes_marks_real_outside_rise_without_estimating(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    candidates = find_candidate_passes(
        _active_satellite_records(),
        station_factory(),
        PARTIAL_START_INTERVAL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.geometry.start_time_utc < PARTIAL_START_INTERVAL[0]
    assert candidate.diagnostics["partial_window"] is True
    assert candidate.diagnostics["start_time_source"] == "extended_search"
    assert candidate.diagnostics["end_time_source"] == "observed"


def test_find_candidate_passes_includes_pass_when_window_only_overlaps_visibility(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    candidates = find_candidate_passes(
        _active_satellite_records(),
        station_factory(),
        OVERLAP_ONLY_INTERVAL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.satellite.tle.name == "ISS (ZARYA)"
    assert candidate.geometry.start_time_utc < OVERLAP_ONLY_INTERVAL[0]
    assert candidate.geometry.culmination_time_utc < OVERLAP_ONLY_INTERVAL[0]
    assert candidate.geometry.end_time_utc > OVERLAP_ONLY_INTERVAL[1]
    assert candidate.diagnostics["partial_window"] is True
    assert candidate.diagnostics["event_sequence"] == []
    assert candidate.diagnostics["start_time_source"] == "extended_search"
    assert candidate.diagnostics["end_time_source"] == "extended_search"
    assert candidate.metrics.satellite_altitude_km == pytest.approx(418.63, abs=0.05)


def test_find_candidate_passes_includes_midnight_overlap_from_previous_day(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    candidates = find_candidate_passes(
        _active_satellite_records(),
        station_factory(),
        MIDNIGHT_OVERLAP_INTERVAL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.satellite.tle.name == "ISS (ZARYA)"
    _assert_datetime_close(
        candidate.geometry.start_time_utc,
        datetime(2026, 6, 18, 23, 54, 46, 794270, tzinfo=timezone.utc),
        tolerance_seconds=1.0,
    )
    _assert_datetime_close(
        candidate.geometry.culmination_time_utc,
        datetime(2026, 6, 18, 23, 58, 4, 271815, tzinfo=timezone.utc),
        tolerance_seconds=1.0,
    )
    _assert_datetime_close(
        candidate.geometry.end_time_utc,
        datetime(2026, 6, 19, 0, 1, 22, 420810, tzinfo=timezone.utc),
        tolerance_seconds=1.0,
    )
    assert candidate.geometry.start_time_utc < MIDNIGHT_OVERLAP_INTERVAL[0]
    assert candidate.geometry.culmination_time_utc < MIDNIGHT_OVERLAP_INTERVAL[0]
    assert candidate.geometry.end_time_utc > MIDNIGHT_OVERLAP_INTERVAL[1]
    assert candidate.diagnostics["partial_window"] is True
    assert candidate.diagnostics["event_sequence"] == []
    assert candidate.diagnostics["start_time_source"] == "extended_search"
    assert candidate.diagnostics["end_time_source"] == "extended_search"


def test_find_candidate_passes_uses_previous_day_rise_instead_of_estimating(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    candidates = find_candidate_passes(
        _active_satellite_records(),
        station_factory(),
        PREVIOUS_DAY_RISE_INTERVAL,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.satellite.tle.name == "ISS (ZARYA)"
    _assert_datetime_close(
        candidate.geometry.start_time_utc,
        datetime(2026, 6, 16, 23, 58, 1, 234897, tzinfo=timezone.utc),
        tolerance_seconds=0.5,
    )
    assert candidate.geometry.start_time_utc < PREVIOUS_DAY_RISE_INTERVAL[0]
    assert candidate.geometry.culmination_time_utc < PREVIOUS_DAY_RISE_INTERVAL[0]
    assert candidate.geometry.end_time_utc > PREVIOUS_DAY_RISE_INTERVAL[1]
    assert candidate.diagnostics["partial_window"] is True
    assert candidate.diagnostics["event_sequence"] == []
    assert candidate.diagnostics["start_time_source"] == "extended_search"
    assert candidate.diagnostics["end_time_source"] == "extended_search"


def test_find_candidate_passes_is_deterministic_for_same_records_and_interval(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes

    records = _active_satellite_records()

    first = find_candidate_passes(records, station_factory(), FULL_PASS_INTERVAL)
    second = find_candidate_passes(records, station_factory(), FULL_PASS_INTERVAL)

    def signature(candidates):
        return [
            (
                candidate.satellite.tle.catalog_number,
                candidate.geometry.start_time_utc.isoformat(),
                candidate.geometry.culmination_time_utc.isoformat(),
                candidate.geometry.end_time_utc.isoformat(),
                round(candidate.geometry.culmination_altitude_deg, 6),
                round(candidate.metrics.satellite_altitude_km, 6),
                round(candidate.metrics.sun_proximity_deg, 6),
            )
            for candidate in candidates
        ]

    assert signature(first) == signature(second)


def test_find_candidate_passes_rejects_invalid_interval(station_factory):
    from tlefinder.core.errors import PropagationError
    from tlefinder.core.pass_analysis import find_candidate_passes

    with pytest.raises(PropagationError, match="interval"):
        find_candidate_passes(
            _active_satellite_records(),
            station_factory(),
            (
                datetime(2026, 5, 12, 15, 2, tzinfo=timezone.utc),
                datetime(2026, 5, 12, 14, 50, tzinfo=timezone.utc),
            ),
        )
