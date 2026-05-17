from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

import pytest

from tlefinder.core.models import RangeConstraint, SatelliteGroup, TargetToleranceConstraint


INVALID_NUMERIC_VALUES = [
    pytest.param(True, id="bool"),
    pytest.param("12.5", id="string"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="infinity"),
]


def test_validation_accepts_valid_ground_station(station_factory):
    from tlefinder.core.validation import validate_ground_station

    validate_ground_station(station_factory())


def test_validation_rejects_latitude_outside_valid_range(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="latitude"):
        validate_ground_station(station_factory(latitude=91.0))


@pytest.mark.parametrize("latitude", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_latitude(station_factory, latitude):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="latitude"):
        validate_ground_station(station_factory(latitude=latitude))


def test_validation_rejects_longitude_outside_valid_range(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="longitude"):
        validate_ground_station(station_factory(longitude=-181.0))


@pytest.mark.parametrize("longitude", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_longitude(station_factory, longitude):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="longitude"):
        validate_ground_station(station_factory(longitude=longitude))


def test_validation_rejects_non_numeric_elevation(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="elevation"):
        validate_ground_station(station_factory(elevation_m="high"))


@pytest.mark.parametrize("elevation_m", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_elevation(station_factory, elevation_m):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="elevation"):
        validate_ground_station(station_factory(elevation_m=elevation_m))


def test_validation_accepts_ground_station_at_8000_meters(station_factory):
    from tlefinder.core.validation import validate_ground_station

    validate_ground_station(station_factory(elevation_m=8000.0))


def test_validation_rejects_elevation_above_8000_meters(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="elevation"):
        validate_ground_station(station_factory(elevation_m=8000.1))


def test_validation_rejects_naive_search_window(search_window_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="timezone"):
        validate_search_window(
            search_window_factory(start_at=datetime(2026, 5, 12, 20, 0))
        )


def test_validation_accepts_utc_search_window(search_window_factory):
    from tlefinder.core.validation import validate_search_window

    validate_search_window(
        search_window_factory(
            start_at=datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
        )
    )


def test_validation_accepts_fixed_offset_search_window(search_window_factory):
    from tlefinder.core.validation import validate_search_window

    validate_search_window(
        search_window_factory(
            start_at=datetime(
                2026,
                5,
                12,
                21,
                0,
                tzinfo=timezone(timedelta(hours=1)),
            )
        )
    )


def test_validation_rejects_timezone_name_search_window(search_window_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="fixed UTC offset"):
        validate_search_window(
            search_window_factory(
                start_at=datetime(
                    2026,
                    5,
                    12,
                    22,
                    0,
                    tzinfo=ZoneInfo("Europe/Paris"),
                )
            )
        )


def test_validation_accepts_search_window_at_30_minutes(search_window_factory):
    from tlefinder.core.validation import validate_search_window

    validate_search_window(search_window_factory(duration_minutes=30))


def test_validation_rejects_search_duration_over_30_minutes(search_window_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="duration"):
        validate_search_window(search_window_factory(duration_minutes=31))


def test_validation_rejects_non_positive_search_duration(search_window_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="duration"):
        validate_search_window(search_window_factory(duration_minutes=0))


@pytest.mark.parametrize("duration_minutes", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_search_duration(
    search_window_factory,
    duration_minutes,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="duration"):
        validate_search_window(search_window_factory(duration_minutes=duration_minutes))


def test_validation_rejects_inconsistent_range(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        culmination_altitude_deg=RangeConstraint(minimum=70.0, maximum=20.0)
    )

    with pytest.raises(ValidationError, match="minimum"):
        validate_search_criteria(criteria)


def test_validation_rejects_culmination_bounds_outside_zero_to_90(
    search_criteria_factory,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        culmination_altitude_deg=RangeConstraint(minimum=-1.0, maximum=45.0)
    )

    with pytest.raises(ValidationError, match="culmination"):
        validate_search_criteria(criteria)


@pytest.mark.parametrize("bound_name", ["minimum", "maximum"])
@pytest.mark.parametrize("bound_value", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_culmination_bounds(
    search_criteria_factory,
    bound_name,
    bound_value,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    bounds = {"minimum": 10.0, "maximum": 80.0}
    bounds[bound_name] = bound_value
    criteria = search_criteria_factory(
        culmination_altitude_deg=RangeConstraint(**bounds)
    )

    with pytest.raises(ValidationError, match=f"culmination_altitude_deg.{bound_name}"):
        validate_search_criteria(criteria)


def test_validation_rejects_invalid_azimuth_target(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        start_azimuth_deg=TargetToleranceConstraint(target=360.0, tolerance=5.0)
    )

    with pytest.raises(ValidationError, match="azimuth"):
        validate_search_criteria(criteria)


@pytest.mark.parametrize("target", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_azimuth_targets(
    search_criteria_factory,
    target,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        start_azimuth_deg=TargetToleranceConstraint(target=target, tolerance=5.0)
    )

    with pytest.raises(ValidationError, match="start_azimuth_deg.target"):
        validate_search_criteria(criteria)


@pytest.mark.parametrize("bound_name", ["minimum", "maximum"])
@pytest.mark.parametrize("bound_value", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_sun_proximity_bounds(
    search_criteria_factory,
    bound_name,
    bound_value,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    bounds = {"minimum": 5.0, "maximum": 60.0}
    bounds[bound_name] = bound_value
    criteria = search_criteria_factory(sun_proximity_deg=RangeConstraint(**bounds))

    with pytest.raises(ValidationError, match=f"sun_proximity_deg.{bound_name}"):
        validate_search_criteria(criteria)


@pytest.mark.parametrize(
    "sun_proximity_deg",
    [
        RangeConstraint(minimum=-0.1, maximum=60.0),
        RangeConstraint(minimum=5.0, maximum=180.1),
    ],
)
def test_validation_rejects_sun_proximity_bounds_outside_zero_to_180(
    search_criteria_factory,
    sun_proximity_deg,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="sun_proximity_deg"):
        validate_search_criteria(
            search_criteria_factory(sun_proximity_deg=sun_proximity_deg)
        )


@pytest.mark.parametrize("bound_name", ["minimum", "maximum"])
@pytest.mark.parametrize("bound_value", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_satellite_altitude_bounds(
    search_criteria_factory,
    bound_name,
    bound_value,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    bounds = {"minimum": 400.0, "maximum": 1200.0}
    bounds[bound_name] = bound_value
    criteria = search_criteria_factory(satellite_altitude_km=RangeConstraint(**bounds))

    with pytest.raises(ValidationError, match=f"satellite_altitude_km.{bound_name}"):
        validate_search_criteria(criteria)


@pytest.mark.parametrize(
    "satellite_altitude_km",
    [
        RangeConstraint(minimum=199.9, maximum=1200.0),
        RangeConstraint(minimum=400.0, maximum=15000.1),
    ],
)
def test_validation_rejects_satellite_altitude_bounds_outside_200_to_15000_km(
    search_criteria_factory,
    satellite_altitude_km,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="satellite_altitude_km"):
        validate_search_criteria(
            search_criteria_factory(satellite_altitude_km=satellite_altitude_km)
        )


@pytest.mark.parametrize(
    "constraint_name",
    [
        "culmination_altitude_deg",
        "sun_proximity_deg",
        "satellite_altitude_km",
    ],
)
def test_validation_rejects_every_range_constraint_with_minimum_above_maximum(
    search_criteria_factory,
    constraint_name,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    ranges = {
        "culmination_altitude_deg": RangeConstraint(minimum=70.0, maximum=20.0),
        "sun_proximity_deg": RangeConstraint(minimum=90.0, maximum=20.0),
        "satellite_altitude_km": RangeConstraint(minimum=1200.0, maximum=400.0),
    }
    criteria = search_criteria_factory(**{constraint_name: ranges[constraint_name]})

    with pytest.raises(ValidationError, match=f"{constraint_name} minimum"):
        validate_search_criteria(criteria)


def test_validation_rejects_score_threshold_outside_zero_to_100(
    search_criteria_factory,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="score_threshold"):
        validate_search_criteria(search_criteria_factory(score_threshold=101.0))


@pytest.mark.parametrize("score_threshold", INVALID_NUMERIC_VALUES)
def test_validation_rejects_non_finite_numeric_score_threshold(
    search_criteria_factory,
    score_threshold,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="score_threshold"):
        validate_search_criteria(
            search_criteria_factory(score_threshold=score_threshold)
        )


def test_validation_rejects_non_positive_result_limit(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="result_limit"):
        validate_search_criteria(search_criteria_factory(result_limit=0))


@pytest.mark.parametrize(
    "result_limit",
    [
        pytest.param(True, id="bool"),
        pytest.param(2.5, id="float"),
        pytest.param("5", id="string"),
    ],
)
def test_validation_rejects_non_integer_result_limit(
    search_criteria_factory,
    result_limit,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="result_limit"):
        validate_search_criteria(search_criteria_factory(result_limit=result_limit))


def test_validation_accepts_disabled_optional_criteria(search_criteria_factory):
    from tlefinder.core.validation import validate_search_criteria

    validate_search_criteria(
        search_criteria_factory(
            culmination_altitude_deg=None,
            culmination_altitude_target_deg=None,
            start_azimuth_deg=None,
            end_azimuth_deg=None,
            culmination_azimuth_deg=None,
            sun_proximity_deg=None,
            satellite_altitude_km=None,
        )
    )


def test_validation_accepts_full_search_request(
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core.models import SatelliteGroup, SearchRequest
    from tlefinder.core.validation import validate_search_request

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group=SatelliteGroup.VISUAL,
    )

    validate_search_request(request)


@pytest.mark.parametrize(
    "satellite_group",
    [
        pytest.param("active", id="raw-string"),
        pytest.param(None, id="none"),
    ],
)
def test_validation_rejects_invalid_satellite_group_values(
    station_factory,
    search_window_factory,
    search_criteria_factory,
    satellite_group,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.models import SearchRequest
    from tlefinder.core.validation import validate_search_request

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group=satellite_group,
    )

    with pytest.raises(ValidationError, match="satellite_group"):
        validate_search_request(request)


def test_validation_rejects_unsupported_enum_like_satellite_group(
    station_factory,
    search_window_factory,
    search_criteria_factory,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.models import SearchRequest
    from tlefinder.core.validation import validate_search_request

    class UnsupportedSatelliteGroup(str, Enum):
        DEBRIS = "debris"

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group=UnsupportedSatelliteGroup.DEBRIS,
    )

    with pytest.raises(ValidationError, match="satellite_group"):
        validate_search_request(request)


@pytest.mark.parametrize("satellite_group", list(SatelliteGroup))
def test_validation_accepts_supported_satellite_groups(
    station_factory,
    search_window_factory,
    search_criteria_factory,
    satellite_group,
):
    from tlefinder.core.models import SearchRequest
    from tlefinder.core.validation import validate_search_request, validate_satellite_group

    request = SearchRequest(
        station=station_factory(),
        window=search_window_factory(),
        criteria=search_criteria_factory(),
        satellite_group=satellite_group,
    )

    validate_satellite_group(satellite_group)
    validate_search_request(request)
