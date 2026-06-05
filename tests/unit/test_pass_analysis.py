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


def _synthetic_record(catalog_number: int):
    from tlefinder.core.models import SatelliteGroup, SatelliteRecord, TleRecord

    epoch = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    catalog = f"{catalog_number:05d}"
    return SatelliteRecord(
        tle=TleRecord(
            name=f"SAT-{catalog}",
            line1=f"1 {catalog}U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
            line2=f"2 {catalog}  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
            catalog_number=catalog_number,
            epoch_utc=epoch,
            source_group=SatelliteGroup.ACTIVE,
            source_path=Path("active.tle"),
        )
    )


def _synthetic_geometry(catalog_number: int):
    from tlefinder.core.models import PassGeometry

    start_time = datetime(2026, 5, 12, 20, catalog_number, tzinfo=timezone.utc)
    return PassGeometry(
        start_time_utc=start_time,
        end_time_utc=start_time + timedelta(minutes=5),
        culmination_time_utc=start_time + timedelta(minutes=2, seconds=30),
        start_azimuth_deg=270.0,
        end_azimuth_deg=90.0,
        culmination_azimuth_deg=180.0,
        culmination_altitude_deg=45.0,
    )


def test_event_search_interval_is_bounded_around_ordinary_window():
    from tlefinder.core.pass_analysis import _event_search_interval

    span_start, span_end = _event_search_interval(*FULL_PASS_INTERVAL)

    assert span_start == datetime(2026, 5, 12, 13, 38, tzinfo=timezone.utc)
    assert span_end == datetime(2026, 5, 12, 16, 14, tzinfo=timezone.utc)
    assert span_start != datetime(2026, 5, 12, 0, 0, tzinfo=timezone.utc)
    assert span_end - span_start < timedelta(hours=4)


def test_event_search_interval_contains_requested_window():
    from tlefinder.core.pass_analysis import _event_search_interval

    span_start, span_end = _event_search_interval(*PARTIAL_END_INTERVAL)

    assert span_start <= PARTIAL_END_INTERVAL[0]
    assert span_end >= PARTIAL_END_INTERVAL[1]


def test_event_search_interval_includes_lookback_for_ongoing_passes():
    from tlefinder.core.pass_analysis import _event_search_interval

    span_start, _ = _event_search_interval(*OVERLAP_ONLY_INTERVAL)

    assert span_start < OVERLAP_ONLY_INTERVAL[0]
    assert OVERLAP_ONLY_INTERVAL[0] - span_start >= timedelta(minutes=15)


def test_event_search_interval_includes_lookahead_for_real_set_events():
    from tlefinder.core.pass_analysis import _event_search_interval

    _, span_end = _event_search_interval(*OVERLAP_ONLY_INTERVAL)

    assert span_end > OVERLAP_ONLY_INTERVAL[1]
    assert span_end - OVERLAP_ONLY_INTERVAL[1] >= timedelta(minutes=15)


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


def test_find_candidate_geometries_with_diagnostics_defers_expensive_metrics(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_geometries_with_diagnostics

    result = find_candidate_geometries_with_diagnostics(
        _active_satellite_records(),
        station_factory(),
        PARTIAL_END_INTERVAL,
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.satellite.tle.name == "ISS (ZARYA)"
    assert candidate.metrics.satellite_altitude_km is None
    assert candidate.metrics.sun_proximity_deg is None
    assert result.diagnostics["satellite_records_inspected"] == 2
    assert result.diagnostics["candidate_geometries_found"] == 1


def test_budgeted_candidate_geometry_search_stops_once_budget_is_reached(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 6)]
    inspected_catalogs: list[int] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )

    def compute_geometry(record, interval, satellite, observer, *, alt_az_recorder=None):
        inspected_catalogs.append(record.tle.catalog_number)
        return _synthetic_geometry(record.tle.catalog_number), {
            "event_count": 3,
            "event_sequence": [0, 1, 2],
            "partial_window": False,
            "event_search_span": {
                "start_utc": "2026-05-12T20:00:00Z",
                "end_utc": "2026-05-12T20:10:00Z",
            },
            "used_event_search_fallback": False,
        }

    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        compute_geometry,
    )

    session = pass_analysis.create_pass_analysis_session(
        station_factory(),
        FULL_PASS_INTERVAL,
    )
    result = session.find_candidate_geometries_with_diagnostics(
        records,
        candidate_budget=2,
    )

    assert inspected_catalogs == [1, 2]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
    ]
    assert result.diagnostics["candidate_budget"] == 2
    assert result.diagnostics["budget_reached"] is True
    assert result.diagnostics["processed_satellite_count"] == 2
    assert result.diagnostics["unprocessed_satellite_count"] == 3
    assert result.diagnostics["processed_candidate_count"] == 2


def test_budgeted_candidate_geometry_search_continues_until_budget_is_reached(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 4)]
    inspected_catalogs: list[int] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )

    def compute_geometry(record, interval, satellite, observer, *, alt_az_recorder=None):
        inspected_catalogs.append(record.tle.catalog_number)
        return _synthetic_geometry(record.tle.catalog_number), {
            "event_count": 3,
            "event_sequence": [0, 1, 2],
            "partial_window": False,
            "event_search_span": {
                "start_utc": "2026-05-12T20:00:00Z",
                "end_utc": "2026-05-12T20:10:00Z",
            },
            "used_event_search_fallback": False,
        }

    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        compute_geometry,
    )

    session = pass_analysis.create_pass_analysis_session(
        station_factory(),
        FULL_PASS_INTERVAL,
    )
    result = session.find_candidate_geometries_with_diagnostics(
        records,
        candidate_budget=5,
    )

    assert inspected_catalogs == [1, 2, 3]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
    ]
    assert result.diagnostics["candidate_budget"] == 5
    assert result.diagnostics["budget_reached"] is False
    assert result.diagnostics["processed_satellite_count"] == 3
    assert result.diagnostics["unprocessed_satellite_count"] == 0
    assert result.diagnostics["processed_candidate_count"] == 3


@pytest.mark.parametrize(
    ("config_kwargs", "message"),
    [
        (
            {"enabled": True, "requested_worker_count": 0},
            "requested_worker_count must be a positive integer",
        ),
        (
            {"enabled": True, "requested_worker_count": True},
            "requested_worker_count must be a positive integer",
        ),
        (
            {"enabled": True, "chunk_size": 0},
            "chunk_size must be a positive integer",
        ),
        (
            {"enabled": True, "chunk_size": 1.5},
            "chunk_size must be a positive integer",
        ),
        (
            {"enabled": True, "backend_name": "thread_pool"},
            "backend_name must be one of",
        ),
    ],
)
def test_parallel_search_config_rejects_invalid_values(config_kwargs, message):
    from tlefinder.core.errors import PropagationError
    from tlefinder.core.pass_analysis import ParallelSearchConfig

    with pytest.raises(PropagationError, match=message):
        ParallelSearchConfig(**config_kwargs)


def test_parallel_search_config_prevents_unbounded_worker_counts():
    from tlefinder.core.errors import PropagationError
    from tlefinder.core import pass_analysis

    with pytest.raises(PropagationError, match="requested_worker_count must be <= "):
        pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=pass_analysis.MAX_PARALLEL_WORKERS + 1,
        )


def test_parallel_search_config_normalizes_one_worker_to_serial():
    from tlefinder.core.pass_analysis import ParallelSearchConfig

    config = ParallelSearchConfig(
        enabled=True,
        requested_worker_count=1,
        chunk_size=4,
    )

    assert config.enabled is False
    assert config.requested_worker_count == 1
    assert config.effective_worker_count == 1
    assert config.chunk_size == 4
    assert config.backend_name == "process_pool"
    assert config.fallback_reason == "single_worker"


def test_exact_parallel_geometry_matches_serial_candidates_and_order(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = _active_satellite_records()
    serial = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
    )

    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(),
    )

    parallel = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=1,
        ),
    )

    assert _candidate_geometry_signature(parallel.candidates) == (
        _candidate_geometry_signature(serial.candidates)
    )
    assert _candidate_diagnostics_signature(parallel.candidates) == (
        _candidate_diagnostics_signature(serial.candidates)
    )
    parallel_diagnostics = dict(parallel.diagnostics)
    assert parallel_diagnostics.pop("parallel_search") == {
        "enabled": True,
        "backend": "process_pool",
        "requested_workers": 2,
        "effective_workers": 2,
        "chunk_size": 1,
        "chunk_count": 2,
    }
    assert parallel_diagnostics == serial.diagnostics


def test_parallel_geometry_submits_stable_input_order_chunks(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 6)]
    captured_inputs = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(captured_inputs=captured_inputs),
    )

    pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=3,
            chunk_size=2,
        ),
    )

    assert [
        (
            chunk_input.start_record_index,
            [record.tle.catalog_number for record in chunk_input.records],
        )
        for chunk_input in captured_inputs
    ] == [
        (0, [1, 2]),
        (2, [3, 4]),
        (4, [5]),
    ]


def test_parallel_geometry_merges_candidates_by_input_order_not_completion_order(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 5)]

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(reverse_results=True),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=4,
            chunk_size=1,
        ),
    )

    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
        4,
    ]
    assert [candidate.diagnostics["worker_catalog"] for candidate in result.candidates] == [
        1,
        2,
        3,
        4,
    ]


def test_parallel_geometry_merges_skipped_record_diagnostics_in_input_order(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 5)]

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_skipped_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(reverse_results=True),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=4,
            chunk_size=1,
        ),
    )

    assert result.candidates == []
    assert [
        diagnostic["catalog_number"]
        for diagnostic in result.diagnostics["skipped_records"]
    ] == [1, 2, 3, 4]
    assert [
        diagnostic["skipped_reason"]
        for diagnostic in result.diagnostics["skipped_records"]
    ] == ["skip-1", "skip-2", "skip-3", "skip-4"]


def test_parallel_geometry_worker_failures_raise_propagation_error(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis
    from tlefinder.core.errors import PropagationError

    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(failure=RuntimeError("worker exploded")),
    )

    with pytest.raises(PropagationError, match="parallel pass geometry worker failed"):
        pass_analysis.find_candidate_geometries_with_diagnostics(
            [_synthetic_record(1), _synthetic_record(2)],
            station_factory(),
            FULL_PASS_INTERVAL,
            parallel_search=pass_analysis.ParallelSearchConfig(
                enabled=True,
                requested_worker_count=2,
                chunk_size=1,
            ),
        )


def test_parallel_geometry_uses_serial_path_for_empty_records(monkeypatch, station_factory):
    from tlefinder.core import pass_analysis

    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _failing_parallel_executor_class(),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        [],
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=1,
        ),
    )

    assert result.candidates == []
    assert result.diagnostics["parallel_search"] == {
        "enabled": False,
        "backend": "process_pool",
        "requested_workers": 2,
        "effective_workers": 1,
        "chunk_size": 1,
        "chunk_count": 0,
        "fallback_reason": "empty_records",
    }


def test_parallel_geometry_uses_serial_path_for_single_chunk_record_sets(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(1), _synthetic_record(2)]

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _failing_parallel_executor_class(),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=4,
            chunk_size=8,
        ),
    )

    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
    ]
    assert result.diagnostics["parallel_search"] == {
        "enabled": False,
        "backend": "process_pool",
        "requested_workers": 4,
        "effective_workers": 1,
        "chunk_size": 8,
        "chunk_count": 1,
        "fallback_reason": "small_record_set",
    }


def test_budgeted_parallel_geometry_processes_chunks_in_deterministic_waves(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 11)]
    wave_inputs: list[list[object]] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _wave_recording_parallel_executor_class(wave_inputs=wave_inputs),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        candidate_budget=5,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=2,
        ),
    )

    assert [
        [
            [record.tle.catalog_number for record in chunk_input.records]
            for chunk_input in wave
        ]
        for wave in wave_inputs
    ] == [
        [[1, 2], [3, 4]],
        [[5, 6], [7, 8]],
    ]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ]
    assert result.diagnostics["candidate_budget"] == 5
    assert result.diagnostics["budget_reached"] is True
    assert result.diagnostics["processed_satellite_count"] == 8
    assert result.diagnostics["unprocessed_satellite_count"] == 2
    assert result.diagnostics["processed_candidate_count"] == 8


def test_budgeted_parallel_geometry_checks_budget_after_wave_merge_not_completion_order(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 5)]
    wave_inputs: list[list[object]] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _wave_recording_parallel_executor_class(
            wave_inputs=wave_inputs,
            reverse_results=True,
        ),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        candidate_budget=1,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=1,
        ),
    )

    assert [
        [
            [record.tle.catalog_number for record in chunk_input.records]
            for chunk_input in wave
        ]
        for wave in wave_inputs
    ] == [[[1], [2]]]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
    ]
    assert result.diagnostics["processed_satellite_count"] == 2
    assert result.diagnostics["unprocessed_satellite_count"] == 2
    assert result.diagnostics["budget_reached"] is True


def test_budgeted_parallel_geometry_does_not_stop_exact_parallel_without_budget(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 7)]
    wave_inputs: list[list[object]] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _wave_recording_parallel_executor_class(wave_inputs=wave_inputs),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=2,
        ),
    )

    assert [
        [
            [record.tle.catalog_number for record in chunk_input.records]
            for chunk_input in wave
        ]
        for wave in wave_inputs
    ] == [
        [[1, 2], [3, 4]],
        [[5, 6]],
    ]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert "candidate_budget" not in result.diagnostics
    assert result.diagnostics["parallel_search"]["enabled"] is True


def test_parallel_geometry_contract_reports_json_friendly_diagnostics(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 6)]
    inspected_catalogs: list[int] = []

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )

    def compute_geometry(record, interval, satellite, observer, *, alt_az_recorder=None):
        inspected_catalogs.append(record.tle.catalog_number)
        return _synthetic_geometry(record.tle.catalog_number), {
            "event_count": 3,
            "event_sequence": [0, 1, 2],
            "partial_window": False,
            "event_search_span": {
                "start_utc": "2026-05-12T20:00:00Z",
                "end_utc": "2026-05-12T20:10:00Z",
            },
            "used_event_search_fallback": False,
        }

    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        _fake_parallel_executor_class(),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=3,
            chunk_size=2,
        ),
    )

    assert inspected_catalogs == [1, 2, 3, 4, 5]
    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
        4,
        5,
    ]
    assert result.diagnostics["parallel_search"] == {
        "enabled": True,
        "backend": "process_pool",
        "requested_workers": 3,
        "effective_workers": 3,
        "chunk_size": 2,
        "chunk_count": 3,
    }
    _assert_json_friendly(result.diagnostics["parallel_search"])


def test_parallel_geometry_contract_reports_single_worker_fallback(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    record = _synthetic_record(1)

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        lambda record, interval, satellite, observer, *, alt_az_recorder=None: (
            _synthetic_geometry(record.tle.catalog_number),
            {
                "event_count": 3,
                "event_sequence": [0, 1, 2],
                "partial_window": False,
                "event_search_span": {
                    "start_utc": "2026-05-12T20:00:00Z",
                    "end_utc": "2026-05-12T20:10:00Z",
                },
                "used_event_search_fallback": False,
            },
        ),
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        [record],
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=1,
            chunk_size=8,
        ),
    )

    assert result.diagnostics["parallel_search"] == {
        "enabled": False,
        "backend": "process_pool",
        "requested_workers": 1,
        "effective_workers": 1,
        "chunk_size": 8,
        "chunk_count": 1,
        "fallback_reason": "single_worker",
    }


def test_parallel_geometry_executor_shutdown_cancels_pending_work(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    records = [_synthetic_record(index) for index in range(1, 4)]
    shutdown_calls: list[tuple[bool, bool]] = []

    class ShutdownRecordingExecutor:
        def __init__(self, max_workers=None, **kwargs):
            self.max_workers = max_workers
            self.kwargs = kwargs

        def map(self, function, inputs):
            return [function(task_input) for task_input in inputs]

        def shutdown(self, *, wait=True, cancel_futures=False):
            shutdown_calls.append((wait, cancel_futures))

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_successful_compute_geometry,
    )
    monkeypatch.setattr(
        pass_analysis,
        "_PROCESS_POOL_EXECUTOR",
        ShutdownRecordingExecutor,
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
        parallel_search=pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=2,
            chunk_size=1,
        ),
    )

    assert [candidate.satellite.tle.catalog_number for candidate in result.candidates] == [
        1,
        2,
        3,
    ]
    assert shutdown_calls == [(True, True)]


def test_large_skipped_record_diagnostics_are_bounded_and_json_friendly(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    record_count = pass_analysis.MAX_SKIPPED_RECORD_DIAGNOSTICS + 5
    records = [_synthetic_record(index) for index in range(1, record_count + 1)]

    monkeypatch.setattr(
        pass_analysis.PassAnalysisSession,
        "_satellite_for",
        lambda self, record: object(),
    )
    monkeypatch.setattr(
        pass_analysis,
        "_compute_pass_geometry_with_context",
        _synthetic_skipped_compute_geometry,
    )

    result = pass_analysis.find_candidate_geometries_with_diagnostics(
        records,
        station_factory(),
        FULL_PASS_INTERVAL,
    )

    assert result.candidates == []
    assert result.diagnostics["skipped_record_count"] == record_count
    assert len(result.diagnostics["skipped_records"]) == (
        pass_analysis.MAX_SKIPPED_RECORD_DIAGNOSTICS
    )
    assert result.diagnostics["skipped_records_truncated"] is True
    assert result.diagnostics["skipped_records_omitted"] == 5
    _assert_json_friendly(result.diagnostics)


def test_pass_analysis_session_reuses_observer_and_satellites_for_deferred_metrics(
    monkeypatch,
    station_factory,
):
    from tlefinder.core import pass_analysis

    original_build_observer = pass_analysis._build_observer
    original_build_satellite = pass_analysis._build_satellite
    observer_calls = 0
    satellite_calls: list[str] = []

    def counting_build_observer(station):
        nonlocal observer_calls
        observer_calls += 1
        return original_build_observer(station)

    def counting_build_satellite(record):
        satellite_calls.append(record.tle.name)
        return original_build_satellite(record)

    monkeypatch.setattr(pass_analysis, "_build_observer", counting_build_observer)
    monkeypatch.setattr(pass_analysis, "_build_satellite", counting_build_satellite)

    session = pass_analysis.create_pass_analysis_session(
        station_factory(),
        FULL_PASS_INTERVAL,
    )
    result = session.find_candidate_geometries_with_diagnostics(
        _active_satellite_records(),
    )
    session.compute_required_metrics(
        result.candidates,
        include_satellite_altitude=True,
        include_sun_proximity=True,
    )

    assert observer_calls == 1
    assert satellite_calls == ["ISS (ZARYA)", "HST"]
    assert result.candidates[0].metrics.satellite_altitude_km == pytest.approx(
        418.63,
        abs=0.05,
    )
    assert result.candidates[0].metrics.sun_proximity_deg == pytest.approx(
        18.0,
        abs=0.5,
    )


def test_pass_analysis_session_computes_only_requested_deferred_metrics(
    station_factory,
):
    from tlefinder.core import pass_analysis

    session = pass_analysis.create_pass_analysis_session(
        station_factory(),
        FULL_PASS_INTERVAL,
    )
    result = session.find_candidate_geometries_with_diagnostics([_iss_record()])
    candidate = result.candidates[0]

    session.compute_required_metrics(
        [candidate],
        include_satellite_altitude=False,
        include_sun_proximity=True,
    )

    assert candidate.metrics.satellite_altitude_km is None
    assert candidate.metrics.sun_proximity_deg == pytest.approx(18.0, abs=0.5)

    session.compute_required_metrics(
        [candidate],
        include_satellite_altitude=True,
        include_sun_proximity=False,
    )

    assert candidate.metrics.satellite_altitude_km == pytest.approx(418.63, abs=0.05)
    assert candidate.metrics.sun_proximity_deg == pytest.approx(18.0, abs=0.5)


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
    assert len(skipped_diagnostics) == 1
    skipped = skipped_diagnostics[0]
    assert skipped["satellite_name"] == "HST"
    assert skipped["catalog_number"] == 20580
    assert skipped["event_count"] == 0
    assert skipped["event_sequence"] == []
    assert skipped["partial_window"] is False
    assert skipped["skipped_reason"] == "no_rise_culmination_pair"
    assert skipped["event_search_span"] == {
        "start_utc": "2026-05-12T13:38:00Z",
        "end_utc": "2026-05-12T16:14:00Z",
    }
    assert skipped["used_event_search_fallback"] is False


def test_find_candidate_passes_with_diagnostics_reports_work_counts_and_span(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes_with_diagnostics

    result = find_candidate_passes_with_diagnostics(
        _active_satellite_records(),
        station_factory(),
        FULL_PASS_INTERVAL,
    )

    assert [candidate.satellite.tle.name for candidate in result.candidates] == [
        "ISS (ZARYA)"
    ]
    assert result.diagnostics == {
        "satellite_records_inspected": 2,
        "candidate_geometries_found": 1,
        "skipped_record_count": 1,
        "skipped_records": [
            {
                "satellite_name": "HST",
                "catalog_number": 20580,
                "event_count": 0,
                "event_sequence": [],
                "partial_window": False,
                "skipped_reason": "no_rise_culmination_pair",
                "event_search_span": {
                    "start_utc": "2026-05-12T13:38:00Z",
                    "end_utc": "2026-05-12T16:14:00Z",
                },
                "used_event_search_fallback": False,
            }
        ],
        "event_search_span": {
            "start_utc": "2026-05-12T13:38:00Z",
            "end_utc": "2026-05-12T16:14:00Z",
        },
    }


def test_pass_analysis_diagnostics_report_bounded_previous_day_overlap_span(
    station_factory,
):
    from tlefinder.core.pass_analysis import find_candidate_passes_with_diagnostics

    result = find_candidate_passes_with_diagnostics(
        _active_satellite_records(),
        station_factory(),
        PREVIOUS_DAY_RISE_INTERVAL,
    )

    assert [candidate.satellite.tle.name for candidate in result.candidates] == [
        "ISS (ZARYA)"
    ]
    assert result.candidates[0].geometry.start_time_utc < PREVIOUS_DAY_RISE_INTERVAL[0]
    assert result.candidates[0].diagnostics["used_event_search_fallback"] is False
    assert result.candidates[0].diagnostics["event_search_span"] == {
        "start_utc": "2026-06-16T23:47:00Z",
        "end_utc": "2026-06-17T00:18:00Z",
    }
    assert result.diagnostics["event_search_span"] == {
        "start_utc": "2026-06-16T23:47:00Z",
        "end_utc": "2026-06-17T00:18:00Z",
    }


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


def _assert_json_friendly(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_friendly(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_friendly(item)
        return
    raise AssertionError(f"non-JSON diagnostic value: {value!r}")


def _fake_parallel_executor_class(
    *,
    captured_inputs=None,
    failure: Exception | None = None,
    reverse_results: bool = False,
):
    class FakeParallelExecutor:
        def __init__(self, max_workers=None, **kwargs):
            self.max_workers = max_workers
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def map(self, function, inputs):
            task_inputs = list(inputs)
            if captured_inputs is not None:
                captured_inputs.extend(task_inputs)
            if failure is not None:
                raise failure
            results = [function(task_input) for task_input in task_inputs]
            if reverse_results:
                return list(reversed(results))
            return results

    return FakeParallelExecutor


def _wave_recording_parallel_executor_class(
    *,
    wave_inputs,
    failure: Exception | None = None,
    reverse_results: bool = False,
):
    class WaveRecordingParallelExecutor:
        def __init__(self, max_workers=None, **kwargs):
            self.max_workers = max_workers
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def map(self, function, inputs):
            task_inputs = list(inputs)
            wave_inputs.append(task_inputs)
            if failure is not None:
                raise failure
            results = [function(task_input) for task_input in task_inputs]
            if reverse_results:
                return list(reversed(results))
            return results

    return WaveRecordingParallelExecutor


def _failing_parallel_executor_class():
    class FailingParallelExecutor:
        def __init__(self, *args, **kwargs):
            raise AssertionError("parallel executor should not be used")

    return FailingParallelExecutor


def _candidate_geometry_signature(candidates):
    return [
        (
            candidate.satellite.tle.catalog_number,
            candidate.geometry.start_time_utc.isoformat(),
            candidate.geometry.culmination_time_utc.isoformat(),
            candidate.geometry.end_time_utc.isoformat(),
            round(candidate.geometry.start_azimuth_deg, 6),
            round(candidate.geometry.culmination_azimuth_deg, 6),
            round(candidate.geometry.end_azimuth_deg, 6),
            round(candidate.geometry.culmination_altitude_deg, 6),
            candidate.metrics.satellite_altitude_km,
            candidate.metrics.sun_proximity_deg,
        )
        for candidate in candidates
    ]


def _candidate_diagnostics_signature(candidates):
    return [
        (
            candidate.satellite.tle.catalog_number,
            candidate.diagnostics,
        )
        for candidate in candidates
    ]


def _synthetic_successful_compute_geometry(
    record,
    interval,
    satellite,
    observer,
    *,
    alt_az_recorder=None,
):
    _ = interval, satellite, observer, alt_az_recorder
    catalog_number = record.tle.catalog_number
    return _synthetic_geometry(catalog_number), {
        "event_count": 3,
        "event_sequence": [0, 1, 2],
        "partial_window": False,
        "worker_catalog": catalog_number,
        "event_search_span": {
            "start_utc": f"2026-05-12T20:{catalog_number:02d}:00Z",
            "end_utc": f"2026-05-12T20:{catalog_number + 1:02d}:00Z",
        },
        "used_event_search_fallback": False,
    }


def _synthetic_skipped_compute_geometry(
    record,
    interval,
    satellite,
    observer,
    *,
    alt_az_recorder=None,
):
    _ = interval, satellite, observer, alt_az_recorder
    catalog_number = record.tle.catalog_number
    return None, {
        "event_count": 0,
        "event_sequence": [],
        "partial_window": False,
        "skipped_reason": f"skip-{catalog_number}",
        "event_search_span": {
            "start_utc": f"2026-05-12T20:{catalog_number:02d}:00Z",
            "end_utc": f"2026-05-12T20:{catalog_number + 1:02d}:00Z",
        },
        "used_event_search_fallback": False,
    }
