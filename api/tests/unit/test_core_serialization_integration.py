from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _candidate():
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        TleRecord,
    )

    epoch = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    return CandidatePass(
        satellite=SatelliteRecord(
            tle=TleRecord(
                name="SAT-25544",
                line1="1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                line2="2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                catalog_number=25544,
                epoch_utc=epoch,
                source_group=SatelliteGroup.ACTIVE,
                source_path=Path("active.tle"),
            )
        ),
        geometry=PassGeometry(
            start_time_utc=epoch,
            end_time_utc=epoch + timedelta(minutes=5),
            culmination_time_utc=epoch + timedelta(minutes=2, seconds=30),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            culmination_azimuth_deg=180.0,
            culmination_altitude_deg=45.0,
        ),
        metrics=PassMetrics(satellite_altitude_km=420.0, sun_proximity_deg=25.0),
    )


def _request():
    from tlefinder.core.models import (
        GroundStation,
        SatelliteGroup,
        SearchCriteria,
        SearchRequest,
        SearchWindow,
    )

    return SearchRequest(
        station=GroundStation(latitude=48.8566, longitude=2.3522, elevation_m=35.0),
        window=SearchWindow(
            start_at=datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
            duration_minutes=10,
        ),
        criteria=SearchCriteria(score_threshold=50.0, result_limit=2),
        satellite_group=SatelliteGroup.ACTIVE,
    )


class DeterministicTimer:
    def __init__(self, step_seconds: float = 0.001):
        self._value = 0.0
        self._step_seconds = step_seconds

    def __call__(self) -> float:
        value = self._value
        self._value += self._step_seconds
        return value


class _FakePassAnalysisSession:
    def __init__(self, candidates, diagnostics: dict[str, Any]):
        self._candidates = list(candidates)
        self._diagnostics = diagnostics

    def find_candidate_geometries_with_diagnostics(self, records):
        from tlefinder.core.pass_analysis import PassAnalysisResult

        return PassAnalysisResult(
            candidates=self._candidates,
            diagnostics=self._diagnostics,
        )

    def compute_required_metrics(
        self,
        candidates,
        *,
        include_satellite_altitude,
        include_sun_proximity,
    ):
        return list(candidates)


def _set_score(candidate, score: float):
    candidate.match_score = score
    return candidate


def _set_rank(candidate, rank: int):
    candidate.rank = rank
    return candidate


def _patch_successful_pipeline(monkeypatch, engine, request, candidates, diagnostics):
    interval = (
        datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 12, 20, 10, tzinfo=timezone.utc),
    )
    records = [candidate.satellite for candidate in candidates]
    monkeypatch.setattr(engine.validation, "validate_search_request", lambda request: None)
    monkeypatch.setattr(engine.time_utils, "build_search_interval", lambda window: interval)
    monkeypatch.setattr(
        engine.tle_repository,
        "load_tle_dataset",
        lambda group, as_of_utc: records,
    )
    monkeypatch.setattr(
        engine.pass_analysis,
        "create_pass_analysis_session",
        lambda station, interval: _FakePassAnalysisSession(candidates, diagnostics),
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_geometry_candidate_passes",
        lambda candidates, criteria: candidates,
    )
    monkeypatch.setattr(
        engine.filtering,
        "filter_metric_candidate_passes",
        lambda candidates, criteria: candidates,
    )
    monkeypatch.setattr(
        engine.scoring,
        "compute_match_score",
        lambda candidate, criteria, interval: _set_score(candidate, 80.0),
    )
    monkeypatch.setattr(
        engine.ranking,
        "apply_score_threshold",
        lambda candidates, threshold: candidates,
    )
    monkeypatch.setattr(
        engine.ranking,
        "rank_candidates",
        lambda candidates: [
            _set_rank(candidate, rank)
            for rank, candidate in enumerate(candidates, start=1)
        ],
    )
    monkeypatch.setattr(
        engine.ranking,
        "limit_results",
        lambda candidates, limit: candidates[:limit],
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


def test_search_diagnostics_are_json_friendly_for_api_and_gui_payloads(monkeypatch):
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core import engine

    request = _request()
    candidate = _candidate()
    _patch_successful_pipeline(
        monkeypatch,
        engine,
        request,
        [candidate],
        {
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
                }
            ],
            "event_search_span": {
                "start_utc": "2026-05-12T00:00:00Z",
                "end_utc": "2026-05-14T00:00:00Z",
            },
        },
    )

    core_response = engine.search_candidates(request, timer=DeterministicTimer())
    api_payload = core_response_to_api_response(core_response).model_dump(mode="json")

    json.dumps(api_payload)
    _assert_json_friendly(api_payload["diagnostics"])
    _assert_json_friendly(api_payload["results"][0]["diagnostics"])
    assert isinstance(api_payload["diagnostics"]["timings_ms"]["pass_analysis"], float)
    assert api_payload["diagnostics"]["pass_analysis"]["event_search_span"] == {
        "start_utc": "2026-05-12T00:00:00Z",
        "end_utc": "2026-05-14T00:00:00Z",
    }

