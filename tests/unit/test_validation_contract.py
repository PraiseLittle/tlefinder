from __future__ import annotations

from datetime import datetime

import pytest


def test_validation_accepts_valid_ground_station(station_factory):
    from tlefinder.core.validation import validate_ground_station

    validate_ground_station(station_factory())


def test_validation_rejects_latitude_outside_valid_range(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="latitude"):
        validate_ground_station(station_factory(latitude=91.0))


def test_validation_rejects_longitude_outside_valid_range(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="longitude"):
        validate_ground_station(station_factory(longitude=-181.0))


def test_validation_rejects_non_numeric_elevation(station_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_ground_station

    with pytest.raises(ValidationError, match="elevation"):
        validate_ground_station(station_factory(elevation_m="high"))


def test_validation_rejects_naive_search_window(search_window_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_window

    with pytest.raises(ValidationError, match="timezone"):
        validate_search_window(
            search_window_factory(start_at=datetime(2026, 5, 12, 20, 0))
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


def test_validation_rejects_inconsistent_range(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.models import RangeConstraint
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
    from tlefinder.core.models import RangeConstraint
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        culmination_altitude_deg=RangeConstraint(minimum=-1.0, maximum=45.0)
    )

    with pytest.raises(ValidationError, match="culmination"):
        validate_search_criteria(criteria)


def test_validation_rejects_invalid_azimuth_target(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.models import TargetToleranceConstraint
    from tlefinder.core.validation import validate_search_criteria

    criteria = search_criteria_factory(
        start_azimuth_deg=TargetToleranceConstraint(target=360.0, tolerance=5.0)
    )

    with pytest.raises(ValidationError, match="azimuth"):
        validate_search_criteria(criteria)


def test_validation_rejects_score_threshold_outside_zero_to_100(
    search_criteria_factory,
):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="score_threshold"):
        validate_search_criteria(search_criteria_factory(score_threshold=101.0))


def test_validation_rejects_non_positive_result_limit(search_criteria_factory):
    from tlefinder.core.errors import ValidationError
    from tlefinder.core.validation import validate_search_criteria

    with pytest.raises(ValidationError, match="result_limit"):
        validate_search_criteria(search_criteria_factory(result_limit=0))


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
