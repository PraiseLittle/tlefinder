from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client_factory(tmp_path):
    def build_client(
        *,
        station_store_path: Path | None = None,
        raise_server_exceptions: bool = True,
    ):
        from tlefinder.api.app import create_app
        from tlefinder.api.config import ApiSettings

        resolved_path = station_store_path or tmp_path / "stations.yaml"
        client = TestClient(
            create_app(ApiSettings(station_store_path=resolved_path)),
            raise_server_exceptions=raise_server_exceptions,
        )
        return client, resolved_path

    return build_client


@pytest.fixture
def station_payload():
    def build_station(**overrides):
        payload = {
            "name": "Paris Observatory",
            "latitude": 48.8367,
            "longitude": 2.3365,
            "elevation_m": 67.0,
        }
        payload.update(overrides)
        return payload

    return build_station


@pytest.fixture
def unnamed_station_payload():
    def build_station(**overrides):
        payload = {
            "latitude": 48.8367,
            "longitude": 2.3365,
            "elevation_m": 67.0,
        }
        payload.update(overrides)
        return payload

    return build_station


@pytest.fixture
def search_window_payload():
    def build_window(**overrides):
        payload = {
            "start_at": "2026-05-12T20:00:00Z",
            "duration_minutes": 10,
        }
        payload.update(overrides)
        return payload

    return build_window


@pytest.fixture
def simple_search_payload(station_payload, search_window_payload):
    def build_payload(**overrides):
        payload = {
            "station": station_payload(),
            "window": search_window_payload(),
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def advanced_search_payload(
    unnamed_station_payload,
    search_window_payload,
):
    def build_payload(**overrides):
        payload = {
            "station": unnamed_station_payload(),
            "window": search_window_payload(),
            "satellite_group": "visual",
            "criteria": {
                "culmination_altitude_deg": {"minimum": 20, "maximum": 80},
                "culmination_altitude_target_deg": {"target": 55, "tolerance": 12},
                "start_azimuth_deg": {"target": 270, "tolerance": 20},
                "end_azimuth_deg": {"target": 90, "tolerance": 10},
                "culmination_azimuth_deg": {"target": 180, "tolerance": 30},
                "sun_proximity_deg": {"minimum": 30, "maximum": 180},
                "satellite_altitude_km": {"minimum": 400, "maximum": 1200},
                "result_limit": 5,
                "score_threshold": 60,
            },
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def core_no_result_response():
    def build_response(**diagnostic_overrides):
        from tlefinder.core.models import SearchResponse, SearchStatus

        diagnostics = {
            "satellite_count": 1200,
            "candidate_count": 0,
            "returned_count": 0,
        }
        diagnostics.update(diagnostic_overrides)
        return SearchResponse(
            results=[],
            status=SearchStatus.NO_RESULT,
            diagnostics=diagnostics,
        )

    return build_response


@pytest.fixture
def core_result_response():
    def build_response(**diagnostic_overrides):
        from tlefinder.core.models import (
            CandidatePass,
            PassGeometry,
            PassMetrics,
            SatelliteGroup,
            SatelliteRecord,
            SearchResponse,
            SearchStatus,
            TleRecord,
        )

        candidate = CandidatePass(
            satellite=SatelliteRecord(
                tle=TleRecord(
                    name="ISS (ZARYA)",
                    line1=(
                        "1 25544U 98067A   26132.50000000  .00000000  "
                        "00000+0  00000+0 0  9991"
                    ),
                    line2=(
                        "2 25544  51.6400 123.4500 0001000  10.0000 "
                        "350.0000 15.50000000000000"
                    ),
                    catalog_number=25544,
                    epoch_utc=datetime(2026, 5, 12, 14, 12, tzinfo=timezone.utc),
                    source_group=SatelliteGroup.ACTIVE,
                    source_path=Path("active.tle"),
                )
            ),
            geometry=PassGeometry(
                start_time_utc=datetime(2026, 5, 12, 20, 2, 10, tzinfo=timezone.utc),
                end_time_utc=datetime(2026, 5, 12, 20, 8, 42, tzinfo=timezone.utc),
                culmination_time_utc=datetime(
                    2026,
                    5,
                    12,
                    20,
                    5,
                    20,
                    tzinfo=timezone.utc,
                ),
                start_azimuth_deg=252.1,
                end_azimuth_deg=63.4,
                culmination_azimuth_deg=319.8,
                culmination_altitude_deg=71.2,
            ),
            metrics=PassMetrics(
                satellite_altitude_km=420.5,
                sun_proximity_deg=118.0,
            ),
            match_score=87.5,
            rank=1,
        )
        diagnostics = {"satellite_count": 1200, "candidate_count": 8, "returned_count": 1}
        diagnostics.update(diagnostic_overrides)
        return SearchResponse(
            results=[candidate],
            status=SearchStatus.RESULTS,
            diagnostics=diagnostics,
        )

    return build_response
