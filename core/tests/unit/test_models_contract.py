from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


def test_shared_request_model_groups_station_window_criteria(
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core.models import SatelliteGroup, SearchRequest, TleAgeLimit

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group=SatelliteGroup.ACTIVE,
    )

    assert request.station.latitude == pytest.approx(48.8566)
    assert request.window.duration_minutes == 10
    assert request.criteria.result_limit == 5
    assert request.satellite_group is SatelliteGroup.ACTIVE
    assert request.tle_age_limit is TleAgeLimit.HOURS_24


def test_shared_response_model_reports_no_result_status():
    from tlefinder.core.models import SearchResponse, SearchStatus

    response = SearchResponse(
        results=[],
        status=SearchStatus.NO_RESULT,
        diagnostics={"reason": "no candidate matched"},
    )

    assert response.results == []
    assert response.status is SearchStatus.NO_RESULT
    assert response.diagnostics["reason"] == "no candidate matched"


def test_phase_2_criteria_excludes_object_type():
    from tlefinder.core.models import SearchCriteria

    with pytest.raises(TypeError, match="object"):
        SearchCriteria(object_type="payload")


def test_candidate_pass_uses_stable_default_diagnostics():
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        TleRecord,
    )

    epoch = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    tle = TleRecord(
        name="ISS",
        line1="1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
        line2="2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
        catalog_number=25544,
        epoch_utc=epoch,
        source_group=SatelliteGroup.ACTIVE,
        source_path=Path("active.tle"),
    )
    satellite = SatelliteRecord(tle=tle)
    geometry = PassGeometry(
        start_time_utc=epoch,
        end_time_utc=epoch,
        culmination_time_utc=epoch,
        start_azimuth_deg=270.0,
        end_azimuth_deg=90.0,
        culmination_azimuth_deg=180.0,
        culmination_altitude_deg=45.0,
    )
    candidate = CandidatePass(
        satellite=satellite,
        geometry=geometry,
        metrics=PassMetrics(satellite_altitude_km=420.0),
    )

    assert candidate.match_score is None
    assert candidate.rank is None
    assert candidate.diagnostics == {}
