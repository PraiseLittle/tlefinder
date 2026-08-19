from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError


def valid_station_payload(**overrides):
    payload = {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    }
    payload.update(overrides)
    return payload


def valid_search_window_payload(**overrides):
    payload = {
        "start_at": "2026-05-12T20:00:00Z",
        "duration_minutes": 10,
    }
    payload.update(overrides)
    return payload


def valid_simple_search_payload(**overrides):
    payload = {
        "station": valid_station_payload(),
        "window": valid_search_window_payload(),
    }
    payload.update(overrides)
    return payload


def valid_result_payload(**overrides):
    payload = {
        "rank": 1,
        "match_score": 87.5,
        "satellite": {
            "name": "ISS (ZARYA)",
            "catalog_number": 25544,
            "tle": {
                "name": "ISS (ZARYA)",
                "line1": "1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                "line2": "2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                "epoch_utc": "2026-05-12T14:12:00Z",
                "source_group": "active",
            },
        },
        "geometry": {
            "start_time_utc": "2026-05-12T20:02:10Z",
            "end_time_utc": "2026-05-12T20:08:42Z",
            "culmination_time_utc": "2026-05-12T20:05:20Z",
            "start_azimuth_deg": 252.1,
            "end_azimuth_deg": 63.4,
            "culmination_azimuth_deg": 319.8,
            "culmination_altitude_deg": 71.2,
        },
        "metrics": {
            "satellite_altitude_km": 420.5,
            "sun_proximity_deg": 118.0,
        },
        "diagnostics": {"source": "fixture"},
    }
    payload.update(overrides)
    return payload


class CustomFixedOffset(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=1)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "CUSTOM+01:00"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("latitude", -90.1, id="latitude-too-low"),
        pytest.param("latitude", 90.1, id="latitude-too-high"),
        pytest.param("latitude", True, id="latitude-bool"),
        pytest.param("latitude", "48.8367", id="latitude-string"),
        pytest.param("longitude", -180.1, id="longitude-too-low"),
        pytest.param("longitude", 180.1, id="longitude-too-high"),
        pytest.param("longitude", False, id="longitude-bool"),
        pytest.param("longitude", "2.3365", id="longitude-string"),
        pytest.param("elevation_m", -500.1, id="elevation-too-low"),
        pytest.param("elevation_m", 8000.1, id="elevation-too-high"),
        pytest.param("elevation_m", True, id="elevation-bool"),
        pytest.param("elevation_m", "67.0", id="elevation-string"),
    ],
)
def test_persisted_station_requires_valid_numeric_coordinates_and_elevation(
    field,
    value,
):
    from tlefinder.api.schemas import PersistedStation

    with pytest.raises(ValidationError):
        PersistedStation.model_validate(valid_station_payload(**{field: value}))


def test_persisted_station_requires_non_empty_trimmed_name():
    from tlefinder.api.schemas import PersistedStation

    station = PersistedStation.model_validate(valid_station_payload(name="  Paris  "))

    assert station.name == "Paris"
    for invalid_name in ("", "   "):
        with pytest.raises(ValidationError):
            PersistedStation.model_validate(valid_station_payload(name=invalid_name))
    with pytest.raises(ValidationError):
        PersistedStation.model_validate(
            {
                "latitude": 48.8367,
                "longitude": 2.3365,
                "elevation_m": 67.0,
            }
        )


def test_search_station_may_omit_name_when_no_persistence_is_needed():
    from tlefinder.api.schemas import SearchStation

    station = SearchStation.model_validate(
        {
            "latitude": 48.8367,
            "longitude": 2.3365,
            "elevation_m": 67.0,
        }
    )

    assert station.name is None


@pytest.mark.parametrize(
    "start_at",
    [
        pytest.param("2026-05-12T20:00:00Z", id="utc-z"),
        pytest.param("2026-05-12T20:00:00+00:00", id="utc-offset"),
        pytest.param("2026-05-12T22:00:00+02:00", id="positive-offset"),
        pytest.param("2026-05-12T15:00:00-05:00", id="negative-offset"),
    ],
)
def test_search_window_accepts_iso_datetime_with_z_or_explicit_utc_offset(start_at):
    from tlefinder.api.schemas import SearchWindow

    window = SearchWindow.model_validate(valid_search_window_payload(start_at=start_at))

    assert window.start_at.utcoffset() is not None


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"duration_minutes": 10}, id="missing-start-at"),
        pytest.param(
            valid_search_window_payload(start_at="2026-05-12T20:00:00"),
            id="missing-offset",
        ),
        pytest.param(
            valid_search_window_payload(start_at="2026-05-12T20:00:00+0100"),
            id="unsupported-offset-shape",
        ),
        pytest.param(
            valid_search_window_payload(start_at="not-a-datetime"),
            id="invalid-datetime",
        ),
        pytest.param(
            valid_search_window_payload(
                start_at=datetime(
                    2026,
                    5,
                    12,
                    22,
                    0,
                    tzinfo=ZoneInfo("Europe/Paris"),
                )
            ),
            id="named-time-zone",
        ),
        pytest.param(
            valid_search_window_payload(
                start_at=datetime(
                    2026,
                    5,
                    12,
                    21,
                    0,
                    tzinfo=CustomFixedOffset(),
                )
            ),
            id="custom-tzinfo",
        ),
    ],
)
def test_search_window_rejects_missing_invalid_or_unsupported_offsets(payload):
    from tlefinder.api.schemas import SearchWindow

    with pytest.raises(ValidationError):
        SearchWindow.model_validate(payload)


@pytest.mark.parametrize(
    "duration_minutes",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(30.1, id="above-maximum"),
        pytest.param(True, id="bool"),
        pytest.param("10", id="string"),
    ],
)
def test_search_window_duration_must_be_greater_than_zero_and_no_more_than_30(
    duration_minutes,
):
    from tlefinder.api.schemas import SearchWindow

    with pytest.raises(ValidationError):
        SearchWindow.model_validate(
            valid_search_window_payload(duration_minutes=duration_minutes)
        )


@pytest.mark.parametrize(
    ("criteria_field", "constraint"),
    [
        pytest.param(
            "culmination_altitude_deg",
            {"minimum": -0.1, "maximum": 45},
            id="culmination-min-too-low",
        ),
        pytest.param(
            "culmination_altitude_deg",
            {"minimum": 10, "maximum": 90.1},
            id="culmination-max-too-high",
        ),
        pytest.param(
            "sun_proximity_deg",
            {"minimum": -0.1, "maximum": 45},
            id="sun-min-too-low",
        ),
        pytest.param(
            "sun_proximity_deg",
            {"minimum": 10, "maximum": 180.1},
            id="sun-max-too-high",
        ),
        pytest.param(
            "satellite_altitude_km",
            {"minimum": 199.9, "maximum": 1000},
            id="satellite-min-too-low",
        ),
        pytest.param(
            "satellite_altitude_km",
            {"minimum": 400, "maximum": 15000.1},
            id="satellite-max-too-high",
        ),
        pytest.param(
            "sun_proximity_deg",
            {"minimum": 90, "maximum": 20},
            id="minimum-greater-than-maximum",
        ),
    ],
)
def test_range_constraints_reject_out_of_bound_values_and_inconsistent_bounds(
    criteria_field,
    constraint,
):
    from tlefinder.api.schemas import AdvancedSearchCriteria

    with pytest.raises(ValidationError):
        AdvancedSearchCriteria.model_validate({criteria_field: constraint})


@pytest.mark.parametrize(
    ("criteria_field", "constraint"),
    [
        pytest.param(
            "start_azimuth_deg",
            {"target": -0.1, "tolerance": 10},
            id="target-too-low",
        ),
        pytest.param(
            "start_azimuth_deg",
            {"target": 360, "tolerance": 10},
            id="target-too-high",
        ),
        pytest.param(
            "end_azimuth_deg",
            {"target": True, "tolerance": 10},
            id="target-bool",
        ),
        pytest.param(
            "culmination_azimuth_deg",
            {"target": "270", "tolerance": 10},
            id="target-string",
        ),
        pytest.param(
            "start_azimuth_deg",
            {"target": 270, "tolerance": -0.1},
            id="tolerance-too-low",
        ),
        pytest.param(
            "start_azimuth_deg",
            {"target": 270, "tolerance": 180.1},
            id="tolerance-too-high",
        ),
        pytest.param(
            "end_azimuth_deg",
            {"target": 90, "tolerance": False},
            id="tolerance-bool",
        ),
    ],
)
def test_azimuth_target_tolerance_constraints_reject_invalid_values(
    criteria_field,
    constraint,
):
    from tlefinder.api.schemas import AdvancedSearchCriteria

    with pytest.raises(ValidationError):
        AdvancedSearchCriteria.model_validate({criteria_field: constraint})


def test_culmination_altitude_target_rejects_values_outside_apparent_altitude_bounds():
    from tlefinder.api.schemas import AdvancedSearchCriteria

    with pytest.raises(ValidationError):
        AdvancedSearchCriteria.model_validate(
            {"culmination_altitude_target_deg": {"target": 90.1, "tolerance": 5}}
        )


@pytest.mark.parametrize(
    "result_limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(True, id="bool"),
        pytest.param(2.5, id="float"),
        pytest.param("5", id="string"),
    ],
)
def test_result_limit_is_a_strictly_positive_integer(result_limit):
    from tlefinder.api.schemas import AdvancedSearchCriteria

    with pytest.raises(ValidationError):
        AdvancedSearchCriteria.model_validate({"result_limit": result_limit})


@pytest.mark.parametrize(
    "score_threshold",
    [
        pytest.param(-0.1, id="too-low"),
        pytest.param(100.1, id="too-high"),
        pytest.param(True, id="bool"),
        pytest.param("60", id="string"),
    ],
)
def test_score_threshold_is_numeric_and_within_zero_to_100(score_threshold):
    from tlefinder.api.schemas import AdvancedSearchCriteria

    with pytest.raises(ValidationError):
        AdvancedSearchCriteria.model_validate({"score_threshold": score_threshold})


@pytest.mark.parametrize("tle_age_limit", ["24h", "1w"])
def test_search_requests_accept_supported_tle_age_limits(tle_age_limit):
    from tlefinder.api.schemas import AdvancedSearchRequest, SimpleSearchRequest

    simple = SimpleSearchRequest.model_validate(
        valid_simple_search_payload(tle_age_limit=tle_age_limit)
    )
    advanced = AdvancedSearchRequest.model_validate(
        valid_simple_search_payload(tle_age_limit=tle_age_limit)
    )

    assert simple.tle_age_limit == tle_age_limit
    assert advanced.tle_age_limit == tle_age_limit


def test_search_requests_default_tle_age_limit_to_24h():
    from tlefinder.api.schemas import AdvancedSearchRequest, SimpleSearchRequest

    simple = SimpleSearchRequest.model_validate(valid_simple_search_payload())
    advanced = AdvancedSearchRequest.model_validate(valid_simple_search_payload())

    assert simple.tle_age_limit == "24h"
    assert advanced.tle_age_limit == "24h"


@pytest.mark.parametrize("tle_age_limit", ["168h", "7d", "week", 168, True])
def test_search_requests_reject_unsupported_tle_age_limits(tle_age_limit):
    from tlefinder.api.schemas import AdvancedSearchRequest, SimpleSearchRequest

    with pytest.raises(ValidationError):
        SimpleSearchRequest.model_validate(
            valid_simple_search_payload(tle_age_limit=tle_age_limit)
        )
    with pytest.raises(ValidationError):
        AdvancedSearchRequest.model_validate(
            valid_simple_search_payload(tle_age_limit=tle_age_limit)
        )


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("criteria", id="criteria"),
        pytest.param("score_threshold", id="threshold"),
        pytest.param("result_limit", id="limit"),
        pytest.param("scoring_config", id="scoring-config"),
        pytest.param("scoring_weights", id="scoring-weights"),
        pytest.param("ranking_rules", id="ranking-rules"),
        pytest.param("unknown", id="unknown"),
    ],
)
def test_simple_search_request_rejects_advanced_and_unknown_fields(field):
    from tlefinder.api.schemas import SimpleSearchRequest

    with pytest.raises(ValidationError):
        SimpleSearchRequest.model_validate(valid_simple_search_payload(**{field: {}}))


def test_advanced_search_request_rejects_unsupported_active_criteria():
    from tlefinder.api.schemas import AdvancedSearchRequest

    with pytest.raises(ValidationError):
        AdvancedSearchRequest.model_validate(
            valid_simple_search_payload(
                criteria={
                    "object_type": "payload",
                    "culmination_altitude_deg": {"minimum": 20, "maximum": 80},
                }
            )
        )


def test_result_response_supports_ranked_candidates_tle_geometry_metrics_diagnostics():
    from tlefinder.api.schemas import SearchResponse

    response = SearchResponse.model_validate(
        {
            "status": "results",
            "results": [valid_result_payload()],
            "diagnostics": {
                "satellite_count": 1200,
                "candidate_count": 8,
                "returned_count": 1,
            },
        }
    )

    dumped = response.model_dump(mode="json")

    assert dumped["status"] == "results"
    assert dumped["results"][0]["rank"] == 1
    assert dumped["results"][0]["match_score"] == 87.5
    assert dumped["results"][0]["satellite"]["catalog_number"] == 25544
    assert dumped["results"][0]["satellite"]["tle"]["source_group"] == "active"
    assert dumped["results"][0]["geometry"]["culmination_altitude_deg"] == 71.2
    assert dumped["results"][0]["metrics"]["sun_proximity_deg"] == 118.0
    assert dumped["results"][0]["diagnostics"] == {"source": "fixture"}
    assert dumped["diagnostics"]["returned_count"] == 1


def test_no_result_response_uses_success_payload_semantics_with_empty_results():
    from tlefinder.api.schemas import SearchResponse

    response = SearchResponse.model_validate(
        {
            "status": "no_result",
            "results": [],
            "diagnostics": {
                "satellite_count": 1200,
                "candidate_count": 0,
                "returned_count": 0,
            },
        }
    )

    assert response.model_dump(mode="json") == {
        "status": "no_result",
        "results": [],
        "diagnostics": {
            "satellite_count": 1200,
            "candidate_count": 0,
            "returned_count": 0,
        },
    }


def test_results_response_requires_at_least_one_result():
    from tlefinder.api.schemas import SearchResponse

    with pytest.raises(ValidationError):
        SearchResponse.model_validate(
            {
                "status": "results",
                "results": [],
                "diagnostics": {
                    "satellite_count": 1200,
                    "candidate_count": 0,
                    "returned_count": 0,
                },
            }
        )


def test_response_datetimes_serialize_with_explicit_utc_reference():
    from tlefinder.api.schemas import SearchResponse

    response = SearchResponse.model_validate(
        {
            "status": "results",
            "results": [
                valid_result_payload(
                    satellite={
                        "name": "ISS (ZARYA)",
                        "catalog_number": 25544,
                        "tle": {
                            "name": "ISS (ZARYA)",
                            "line1": "1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                            "line2": "2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                            "epoch_utc": datetime(
                                2026,
                                5,
                                12,
                                16,
                                12,
                                tzinfo=timezone(timedelta(hours=2)),
                            ),
                            "source_group": "active",
                        },
                    },
                    geometry={
                        "start_time_utc": datetime(
                            2026,
                            5,
                            12,
                            22,
                            2,
                            10,
                            tzinfo=timezone(timedelta(hours=2)),
                        ),
                        "end_time_utc": "2026-05-12T20:08:42+00:00",
                        "culmination_time_utc": "2026-05-12T20:05:20Z",
                        "start_azimuth_deg": 252.1,
                        "end_azimuth_deg": 63.4,
                        "culmination_azimuth_deg": 319.8,
                        "culmination_altitude_deg": 71.2,
                    },
                )
            ],
            "diagnostics": {},
        }
    )

    dumped = response.model_dump(mode="json")

    assert dumped["results"][0]["satellite"]["tle"]["epoch_utc"] == (
        "2026-05-12T14:12:00Z"
    )
    assert dumped["results"][0]["geometry"]["start_time_utc"] == (
        "2026-05-12T20:02:10Z"
    )
    assert dumped["results"][0]["geometry"]["end_time_utc"].endswith("Z")
    assert dumped["results"][0]["geometry"]["culmination_time_utc"].endswith("Z")


def test_error_response_uses_stable_error_envelope():
    from tlefinder.api.schemas import ApiError, ErrorResponse, FieldError

    response = ErrorResponse(
        error=ApiError(
            code="validation_error",
            message="Request validation failed.",
            details={"source": "body"},
            field_errors=[
                FieldError(
                    field="window.duration_minutes",
                    message="duration_minutes must be greater than 0",
                )
            ],
        )
    )

    assert response.model_dump(mode="json") == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": {"source": "body"},
            "field_errors": [
                {
                    "field": "window.duration_minutes",
                    "message": "duration_minutes must be greater than 0",
                }
            ],
        }
    }


def test_field_error_requires_field_path_and_readable_message():
    from tlefinder.api.schemas import FieldError

    field_error = FieldError(
        field="criteria.result_limit",
        message="result_limit must be a strictly positive integer",
    )

    assert field_error.field == "criteria.result_limit"
    assert field_error.message == "result_limit must be a strictly positive integer"
    with pytest.raises(ValidationError):
        FieldError(field="", message="result_limit must be a strictly positive integer")
    with pytest.raises(ValidationError):
        FieldError(field="criteria.result_limit", message="")
