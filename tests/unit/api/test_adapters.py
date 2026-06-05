from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError


def search_station_payload(**overrides):
    payload = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    payload.update(overrides)
    return payload


def search_window_payload(**overrides):
    payload = {
        "start_at": "2026-05-12T22:00:00+02:00",
        "duration_minutes": 10,
    }
    payload.update(overrides)
    return payload


def simple_search_request(**overrides):
    from tlefinder.api.schemas import SimpleSearchRequest

    payload = {
        "station": search_station_payload(),
        "window": search_window_payload(),
    }
    payload.update(overrides)
    return SimpleSearchRequest.model_validate(payload)


def advanced_search_request(**overrides):
    from tlefinder.api.schemas import AdvancedSearchRequest

    payload = {
        "station": search_station_payload(),
        "window": search_window_payload(),
    }
    payload.update(overrides)
    return AdvancedSearchRequest.model_validate(payload)


def candidate_pass(**overrides):
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        TleRecord,
    )

    rank = overrides.pop("rank", 1)
    name = overrides.pop("name", "ISS (ZARYA)")
    catalog_number = overrides.pop("catalog_number", 25544)
    source_group = overrides.pop("source_group", SatelliteGroup.ACTIVE)
    match_score = overrides.pop("match_score", 87.5)
    diagnostics = overrides.pop("diagnostics", {"source": "fixture"})

    tle = TleRecord(
        name=name,
        line1=overrides.pop(
            "line1",
            "1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
        ),
        line2=overrides.pop(
            "line2",
            "2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
        ),
        catalog_number=catalog_number,
        epoch_utc=overrides.pop(
            "epoch_utc",
            datetime(2026, 5, 12, 16, 12, tzinfo=timezone(timedelta(hours=2))),
        ),
        source_group=source_group,
        source_path=Path("fixtures/active.tle"),
    )
    geometry = PassGeometry(
        start_time_utc=overrides.pop(
            "start_time_utc",
            datetime(2026, 5, 12, 22, 2, 10, tzinfo=timezone(timedelta(hours=2))),
        ),
        end_time_utc=overrides.pop(
            "end_time_utc",
            datetime(2026, 5, 12, 20, 8, 42, tzinfo=timezone.utc),
        ),
        culmination_time_utc=overrides.pop(
            "culmination_time_utc",
            datetime(2026, 5, 12, 20, 5, 20, tzinfo=timezone.utc),
        ),
        start_azimuth_deg=overrides.pop("start_azimuth_deg", 252.1),
        end_azimuth_deg=overrides.pop("end_azimuth_deg", 63.4),
        culmination_azimuth_deg=overrides.pop("culmination_azimuth_deg", 319.8),
        culmination_altitude_deg=overrides.pop("culmination_altitude_deg", 71.2),
    )
    metrics = PassMetrics(
        satellite_altitude_km=overrides.pop("satellite_altitude_km", 420.5),
        sun_proximity_deg=overrides.pop("sun_proximity_deg", 118.0),
    )

    if overrides:
        raise AssertionError(f"Unhandled candidate overrides: {sorted(overrides)}")

    return CandidatePass(
        satellite=SatelliteRecord(tle=tle),
        geometry=geometry,
        metrics=metrics,
        match_score=match_score,
        rank=rank,
        diagnostics=diagnostics,
    )


def test_simple_search_maps_station_fields_to_core_ground_station():
    from tlefinder.api.adapters import simple_search_to_core_request
    from tlefinder.core.models import GroundStation

    core_request = simple_search_to_core_request(simple_search_request())

    assert isinstance(core_request.station, GroundStation)
    assert core_request.station.latitude == 48.8367
    assert core_request.station.longitude == 2.3365
    assert core_request.station.elevation_m == 67.0


def test_simple_search_maps_window_start_to_timezone_aware_core_window():
    from tlefinder.api.adapters import simple_search_to_core_request
    from tlefinder.core.models import SearchWindow

    core_request = simple_search_to_core_request(simple_search_request())

    assert isinstance(core_request.window, SearchWindow)
    assert core_request.window.start_at == datetime(
        2026,
        5,
        12,
        22,
        0,
        tzinfo=timezone(timedelta(hours=2)),
    )
    assert core_request.window.start_at.utcoffset() == timedelta(hours=2)
    assert core_request.window.duration_minutes == 10


def test_simple_search_uses_active_satellite_group():
    from tlefinder.api.adapters import simple_search_to_core_request
    from tlefinder.core.models import SatelliteGroup

    core_request = simple_search_to_core_request(simple_search_request())

    assert core_request.satellite_group is SatelliteGroup.ACTIVE


def test_simple_search_applies_culmination_altitude_defaults():
    from tlefinder.api.adapters import simple_search_to_core_request

    core_request = simple_search_to_core_request(simple_search_request())

    assert core_request.criteria.culmination_altitude_deg is not None
    assert core_request.criteria.culmination_altitude_deg.minimum == 0.0
    assert core_request.criteria.culmination_altitude_deg.maximum == 90.0


def test_simple_search_disables_all_azimuth_preferences():
    from tlefinder.api.adapters import simple_search_to_core_request

    core_request = simple_search_to_core_request(simple_search_request())

    assert core_request.criteria.start_azimuth_deg is None
    assert core_request.criteria.end_azimuth_deg is None
    assert core_request.criteria.culmination_azimuth_deg is None


def test_simple_search_applies_sun_and_satellite_altitude_defaults():
    from tlefinder.api.adapters import simple_search_to_core_request

    core_request = simple_search_to_core_request(simple_search_request())

    assert core_request.criteria.sun_proximity_deg is not None
    assert core_request.criteria.sun_proximity_deg.minimum == 0.0
    assert core_request.criteria.sun_proximity_deg.maximum == 180.0
    assert core_request.criteria.satellite_altitude_km is not None
    assert core_request.criteria.satellite_altitude_km.minimum == 200.0
    assert core_request.criteria.satellite_altitude_km.maximum == 2000.0


def test_simple_search_applies_limit_and_disabled_score_threshold_defaults():
    from tlefinder.api.adapters import simple_search_to_core_request

    core_request = simple_search_to_core_request(simple_search_request())

    assert core_request.criteria.result_limit == 10
    assert core_request.criteria.score_threshold == 0.0


def test_simple_search_does_not_expose_scoring_configuration_or_workflow_labels():
    from tlefinder.api.adapters import simple_search_to_core_request

    core_request = simple_search_to_core_request(simple_search_request())

    for unsupported_attribute in (
        "scoring_config",
        "scoring_weights",
        "ranking_rules",
        "workflow_label",
    ):
        assert not hasattr(core_request, unsupported_attribute)
        assert not hasattr(core_request.criteria, unsupported_attribute)


def test_advanced_search_omitted_satellite_group_defaults_to_active():
    from tlefinder.api.adapters import advanced_search_to_core_request
    from tlefinder.core.models import SatelliteGroup

    core_request = advanced_search_to_core_request(advanced_search_request())

    assert core_request.satellite_group is SatelliteGroup.ACTIVE


@pytest.mark.parametrize(
    ("api_group", "core_group"),
    [
        pytest.param("active", "ACTIVE", id="active"),
        pytest.param("visual", "VISUAL", id="visual"),
        pytest.param("amateur", "AMATEUR", id="amateur"),
    ],
)
def test_advanced_search_supported_satellite_groups_map_to_core_enum(
    api_group,
    core_group,
):
    from tlefinder.api.adapters import advanced_search_to_core_request
    from tlefinder.core.models import SatelliteGroup

    core_request = advanced_search_to_core_request(
        advanced_search_request(satellite_group=api_group)
    )

    assert core_request.satellite_group is getattr(SatelliteGroup, core_group)


def test_advanced_search_maps_culmination_altitude_range_and_target_criteria():
    from tlefinder.api.adapters import advanced_search_to_core_request

    core_request = advanced_search_to_core_request(
        advanced_search_request(
            criteria={
                "culmination_altitude_deg": {"minimum": 20, "maximum": 80},
                "culmination_altitude_target_deg": {
                    "target": 55,
                    "tolerance": 12,
                },
            }
        )
    )

    assert core_request.criteria.culmination_altitude_deg is not None
    assert core_request.criteria.culmination_altitude_deg.minimum == 20.0
    assert core_request.criteria.culmination_altitude_deg.maximum == 80.0
    assert core_request.criteria.culmination_altitude_target_deg is not None
    assert core_request.criteria.culmination_altitude_target_deg.target == 55.0
    assert core_request.criteria.culmination_altitude_target_deg.tolerance == 12.0


def test_advanced_search_maps_start_end_and_culmination_azimuth_independently():
    from tlefinder.api.adapters import advanced_search_to_core_request

    core_request = advanced_search_to_core_request(
        advanced_search_request(
            criteria={
                "start_azimuth_deg": {"target": 270, "tolerance": 20},
                "end_azimuth_deg": {"target": 90, "tolerance": 10},
                "culmination_azimuth_deg": {"target": 180, "tolerance": 30},
            }
        )
    )

    assert core_request.criteria.start_azimuth_deg is not None
    assert core_request.criteria.start_azimuth_deg.target == 270.0
    assert core_request.criteria.start_azimuth_deg.tolerance == 20.0
    assert core_request.criteria.end_azimuth_deg is not None
    assert core_request.criteria.end_azimuth_deg.target == 90.0
    assert core_request.criteria.end_azimuth_deg.tolerance == 10.0
    assert core_request.criteria.culmination_azimuth_deg is not None
    assert core_request.criteria.culmination_azimuth_deg.target == 180.0
    assert core_request.criteria.culmination_azimuth_deg.tolerance == 30.0


def test_advanced_search_maps_sun_and_satellite_altitude_ranges():
    from tlefinder.api.adapters import advanced_search_to_core_request

    core_request = advanced_search_to_core_request(
        advanced_search_request(
            criteria={
                "sun_proximity_deg": {"minimum": 30, "maximum": 180},
                "satellite_altitude_km": {"minimum": 400, "maximum": 1200},
            }
        )
    )

    assert core_request.criteria.sun_proximity_deg is not None
    assert core_request.criteria.sun_proximity_deg.minimum == 30.0
    assert core_request.criteria.sun_proximity_deg.maximum == 180.0
    assert core_request.criteria.satellite_altitude_km is not None
    assert core_request.criteria.satellite_altitude_km.minimum == 400.0
    assert core_request.criteria.satellite_altitude_km.maximum == 1200.0


def test_advanced_search_maps_result_limit_and_score_threshold():
    from tlefinder.api.adapters import advanced_search_to_core_request

    core_request = advanced_search_to_core_request(
        advanced_search_request(
            criteria={
                "result_limit": 5,
                "score_threshold": 60,
            }
        )
    )

    assert core_request.criteria.result_limit == 5
    assert core_request.criteria.score_threshold == 60.0


def test_advanced_search_omitted_optional_criteria_remain_disabled_or_core_defaults():
    from tlefinder.api.adapters import advanced_search_to_core_request

    core_request = advanced_search_to_core_request(advanced_search_request())

    assert core_request.criteria.culmination_altitude_deg is None
    assert core_request.criteria.culmination_altitude_target_deg is None
    assert core_request.criteria.start_azimuth_deg is None
    assert core_request.criteria.end_azimuth_deg is None
    assert core_request.criteria.culmination_azimuth_deg is None
    assert core_request.criteria.sun_proximity_deg is None
    assert core_request.criteria.satellite_altitude_km is None
    assert core_request.criteria.result_limit == 10
    assert core_request.criteria.score_threshold == 0.0


def test_advanced_search_unsupported_criteria_are_rejected_before_adapter_code_runs():
    from tlefinder.api.schemas import AdvancedSearchRequest

    with pytest.raises(ValidationError):
        AdvancedSearchRequest.model_validate(
            {
                "station": search_station_payload(),
                "window": search_window_payload(),
                "criteria": {
                    "object_type": "payload",
                    "result_limit": 5,
                },
            }
        )


def test_core_response_serialization_preserves_ranked_result_order():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[
                candidate_pass(rank=1, name="BESTSAT", catalog_number=10001),
                candidate_pass(rank=2, name="SECONDSAT", catalog_number=10002),
            ],
            status=SearchStatus.RESULTS,
            diagnostics={"returned_count": 2},
        )
    )

    dumped = api_response.model_dump(mode="json")

    assert [result["rank"] for result in dumped["results"]] == [1, 2]
    assert [
        result["satellite"]["name"] for result in dumped["results"]
    ] == ["BESTSAT", "SECONDSAT"]


def test_core_response_serialization_preserves_scores_tle_epoch_and_source_group():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[candidate_pass(match_score=91.25)],
            status=SearchStatus.RESULTS,
            diagnostics={},
        )
    )

    result = api_response.model_dump(mode="json")["results"][0]

    assert result["match_score"] == 91.25
    assert result["satellite"]["tle"]["line1"].startswith("1 25544U")
    assert result["satellite"]["tle"]["line2"].startswith("2 25544")
    assert result["satellite"]["tle"]["epoch_utc"] == "2026-05-12T14:12:00Z"
    assert result["satellite"]["tle"]["source_group"] == "active"


def test_core_response_serialization_converts_pass_times_to_utc_iso_strings():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[candidate_pass()],
            status=SearchStatus.RESULTS,
            diagnostics={},
        )
    )

    geometry = api_response.model_dump(mode="json")["results"][0]["geometry"]

    assert geometry["start_time_utc"] == "2026-05-12T20:02:10Z"
    assert geometry["end_time_utc"] == "2026-05-12T20:08:42Z"
    assert geometry["culmination_time_utc"] == "2026-05-12T20:05:20Z"


def test_core_response_serialization_preserves_geometry_angles_metrics_and_diagnostics():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[
                candidate_pass(
                    start_azimuth_deg=250.5,
                    end_azimuth_deg=65.25,
                    culmination_azimuth_deg=315.75,
                    culmination_altitude_deg=72.5,
                    satellite_altitude_km=421.5,
                    sun_proximity_deg=119.5,
                    diagnostics={"pass_id": "candidate-1"},
                )
            ],
            status=SearchStatus.RESULTS,
            diagnostics={
                "satellite_count": 1200,
                "candidate_count": 8,
                "returned_count": 1,
            },
        )
    )

    dumped = api_response.model_dump(mode="json")
    result = dumped["results"][0]

    assert result["geometry"]["start_azimuth_deg"] == 250.5
    assert result["geometry"]["end_azimuth_deg"] == 65.25
    assert result["geometry"]["culmination_azimuth_deg"] == 315.75
    assert result["geometry"]["culmination_altitude_deg"] == 72.5
    assert result["metrics"]["satellite_altitude_km"] == 421.5
    assert result["metrics"]["sun_proximity_deg"] == 119.5
    assert result["diagnostics"] == {"pass_id": "candidate-1"}
    assert dumped["diagnostics"] == {
        "satellite_count": 1200,
        "candidate_count": 8,
        "returned_count": 1,
    }


def test_core_response_serialization_preserves_budget_and_parallel_diagnostics():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    diagnostics = {
        "candidate_budget": {
            "requested": True,
            "enabled": True,
            "disabled_reason": None,
            "candidate_budget": 60,
            "budget_reached": True,
            "processed_satellite_count": 128,
            "unprocessed_satellite_count": 64,
            "processed_candidate_count": 62,
            "returned_candidate_count": 10,
            "approximate": True,
            "approximation_note": (
                "Budgeted results are approximate because unseen satellites might "
                "have scored higher."
            ),
        },
        "parallel_search": {
            "enabled": True,
            "backend": "process_pool",
            "requested_workers": 4,
            "effective_workers": 4,
            "chunk_size": 32,
            "chunk_count": 6,
        },
    }

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[candidate_pass()],
            status=SearchStatus.RESULTS,
            diagnostics=diagnostics,
        )
    )

    assert api_response.model_dump(mode="json")["diagnostics"] == diagnostics


def test_core_no_result_response_serializes_as_empty_success_payload():
    from tlefinder.api.adapters import core_response_to_api_response
    from tlefinder.core.models import SearchResponse as CoreSearchResponse
    from tlefinder.core.models import SearchStatus

    api_response = core_response_to_api_response(
        CoreSearchResponse(
            results=[],
            status=SearchStatus.NO_RESULT,
            diagnostics={
                "satellite_count": 1200,
                "candidate_count": 0,
                "returned_count": 0,
            },
        )
    )

    assert api_response.model_dump(mode="json") == {
        "status": "no_result",
        "results": [],
        "diagnostics": {
            "satellite_count": 1200,
            "candidate_count": 0,
            "returned_count": 0,
        },
    }
