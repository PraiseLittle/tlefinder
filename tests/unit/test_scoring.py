from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _candidate(
    *,
    catalog_number: int = 25544,
    start_offset_minutes: float = 0.0,
    duration_minutes: float = 5.0,
    culmination_altitude_deg: float = 45.0,
    start_azimuth_deg: float = 270.0,
    end_azimuth_deg: float = 90.0,
    culmination_azimuth_deg: float = 180.0,
    sun_proximity_deg: float | None = 60.0,
):
    from tlefinder.core.models import (
        CandidatePass,
        PassGeometry,
        PassMetrics,
        SatelliteGroup,
        SatelliteRecord,
        TleRecord,
    )

    epoch = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    start_time = epoch + timedelta(minutes=start_offset_minutes)
    end_time = start_time + timedelta(minutes=duration_minutes)
    catalog = f"{catalog_number:05d}"
    return CandidatePass(
        satellite=SatelliteRecord(
            tle=TleRecord(
                name=f"SAT-{catalog}",
                line1=f"1 {catalog}U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991",
                line2=f"2 {catalog}  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000",
                catalog_number=catalog_number,
                epoch_utc=epoch,
                source_group=SatelliteGroup.ACTIVE,
                source_path=Path("active.tle"),
            )
        ),
        geometry=PassGeometry(
            start_time_utc=start_time,
            end_time_utc=end_time,
            culmination_time_utc=start_time + (end_time - start_time) / 2,
            start_azimuth_deg=start_azimuth_deg,
            end_azimuth_deg=end_azimuth_deg,
            culmination_azimuth_deg=culmination_azimuth_deg,
            culmination_altitude_deg=culmination_altitude_deg,
        ),
        metrics=PassMetrics(
            satellite_altitude_km=420.0,
            sun_proximity_deg=sun_proximity_deg,
        ),
    )


def _interval(*, duration_minutes: float = 10.0):
    start = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    return (start, start + timedelta(minutes=duration_minutes))


def test_culmination_score_is_linear_on_target_tolerance():
    from tlefinder.core.models import SearchCriteria, TargetToleranceConstraint
    from tlefinder.core.scoring import score_culmination_fit

    criteria = SearchCriteria(
        culmination_altitude_target_deg=TargetToleranceConstraint(
            target=60.0,
            tolerance=30.0,
        )
    )

    assert score_culmination_fit(
        _candidate(culmination_altitude_deg=60.0),
        criteria,
    ) == pytest.approx(100.0)
    assert score_culmination_fit(
        _candidate(culmination_altitude_deg=45.0),
        criteria,
    ) == pytest.approx(50.0)
    assert score_culmination_fit(
        _candidate(culmination_altitude_deg=30.0),
        criteria,
    ) == pytest.approx(0.0)


def test_azimuth_score_uses_shortest_circular_distance():
    from tlefinder.core.models import SearchCriteria, TargetToleranceConstraint
    from tlefinder.core.scoring import score_azimuth_fit

    criteria = SearchCriteria(
        start_azimuth_deg=TargetToleranceConstraint(target=350.0, tolerance=20.0)
    )

    assert score_azimuth_fit(_candidate(start_azimuth_deg=350.0), criteria) == 100.0
    assert score_azimuth_fit(_candidate(start_azimuth_deg=0.0), criteria) == 50.0
    assert score_azimuth_fit(_candidate(start_azimuth_deg=5.0), criteria) == 25.0


def test_sun_proximity_score_prefers_center_of_bounded_range():
    from tlefinder.core.models import RangeConstraint, SearchCriteria
    from tlefinder.core.scoring import score_sun_proximity_fit

    criteria = SearchCriteria(
        sun_proximity_deg=RangeConstraint(minimum=20.0, maximum=100.0)
    )

    assert score_sun_proximity_fit(_candidate(sun_proximity_deg=60.0), criteria) == 100.0
    assert score_sun_proximity_fit(_candidate(sun_proximity_deg=40.0), criteria) == 50.0
    assert score_sun_proximity_fit(_candidate(sun_proximity_deg=20.0), criteria) == 0.0


def test_compute_match_score_uses_equal_weights_across_enabled_criteria():
    from tlefinder.core.models import (
        RangeConstraint,
        SearchCriteria,
        TargetToleranceConstraint,
    )
    from tlefinder.core.scoring import compute_match_score

    candidate = _candidate(
        culmination_altitude_deg=60.0,
        start_azimuth_deg=0.0,
        sun_proximity_deg=60.0,
    )
    criteria = SearchCriteria(
        culmination_altitude_target_deg=TargetToleranceConstraint(
            target=50.0,
            tolerance=20.0,
        ),
        start_azimuth_deg=TargetToleranceConstraint(target=350.0, tolerance=20.0),
        sun_proximity_deg=RangeConstraint(minimum=20.0, maximum=100.0),
    )

    scored = compute_match_score(candidate, criteria, _interval())

    assert scored is candidate
    assert scored.match_score == pytest.approx(
        (50.0 + 100.0 + 50.0 + 50.0 + 100.0) / 5.0
    )


def test_compute_match_score_has_no_hidden_weight_for_disabled_optional_criteria():
    from tlefinder.core.models import (
        RangeConstraint,
        SearchCriteria,
        TargetToleranceConstraint,
    )
    from tlefinder.core.scoring import compute_match_score

    candidate = _candidate(start_azimuth_deg=5.0)
    interval = _interval()

    default_score = compute_match_score(_candidate(), SearchCriteria(), interval).match_score
    assert default_score == pytest.approx(75.0)
    assert compute_match_score(
        _candidate(),
        SearchCriteria(satellite_altitude_km=RangeConstraint(minimum=200.0)),
        interval,
    ).match_score == pytest.approx(default_score)
    assert compute_match_score(
        candidate,
        SearchCriteria(
            start_azimuth_deg=TargetToleranceConstraint(
                target=350.0,
                tolerance=20.0,
            )
        ),
        interval,
    ).match_score == pytest.approx((50.0 + 100.0 + 25.0) / 3.0)


def test_pass_duration_score_is_derived_from_geometry_duration():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_duration_fit

    candidate = _candidate(duration_minutes=7.0)

    assert score_pass_duration_fit(candidate, SearchCriteria(), _interval()) == 70.0


def test_longer_candidate_pass_receives_higher_duration_score():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_duration_fit

    criteria = SearchCriteria()
    interval = _interval()

    assert score_pass_duration_fit(
        _candidate(duration_minutes=8.0),
        criteria,
        interval,
    ) > score_pass_duration_fit(
        _candidate(duration_minutes=2.0),
        criteria,
        interval,
    )


@pytest.mark.parametrize(
    ("duration_minutes", "expected_score"),
    [
        (0.0, 0.0),
        (5.0, 50.0),
        (10.0, 100.0),
        (15.0, 100.0),
    ],
)
def test_duration_score_is_normalized_on_zero_to_100_scale(
    duration_minutes,
    expected_score,
):
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_duration_fit

    assert score_pass_duration_fit(
        _candidate(duration_minutes=duration_minutes),
        SearchCriteria(),
        _interval(),
    ) == pytest.approx(expected_score)


def test_pass_timing_uses_actual_start_not_clipped_window_start():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_timing_fit

    criteria = SearchCriteria()
    interval = _interval()

    assert score_pass_timing_fit(
        _candidate(start_offset_minutes=-1.0),
        criteria,
        interval,
    ) > score_pass_timing_fit(
        _candidate(start_offset_minutes=-5.0),
        criteria,
        interval,
    )


def test_after_start_pass_scores_higher_than_before_start_pass():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_timing_fit

    criteria = SearchCriteria()
    interval = _interval()

    assert score_pass_timing_fit(
        _candidate(start_offset_minutes=9.0),
        criteria,
        interval,
    ) > score_pass_timing_fit(
        _candidate(start_offset_minutes=-0.5),
        criteria,
        interval,
    )
    assert score_pass_timing_fit(
        _candidate(start_offset_minutes=1.0),
        criteria,
        interval,
    ) > score_pass_timing_fit(
        _candidate(start_offset_minutes=-1.0),
        criteria,
        interval,
    )


def test_after_start_timing_prefers_closer_pass_starts():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_timing_fit

    criteria = SearchCriteria()
    interval = _interval()

    assert score_pass_timing_fit(
        _candidate(start_offset_minutes=1.0),
        criteria,
        interval,
    ) > score_pass_timing_fit(
        _candidate(start_offset_minutes=5.0),
        criteria,
        interval,
    )


@pytest.mark.parametrize(
    ("start_offset_minutes", "expected_score"),
    [
        (-12.0, 0.0),
        (-10.0, 0.0),
        (-5.0, 25.0),
        (-1.0, 45.0),
        (0.0, 100.0),
        (1.0, 95.0),
        (5.0, 75.0),
        (10.0, 50.0),
        (12.0, 0.0),
    ],
)
def test_timing_score_is_normalized_on_zero_to_100_scale(
    start_offset_minutes,
    expected_score,
):
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_timing_fit

    assert score_pass_timing_fit(
        _candidate(start_offset_minutes=start_offset_minutes),
        SearchCriteria(),
        _interval(),
    ) == pytest.approx(expected_score)


def test_in_progress_passes_no_longer_all_receive_perfect_timing_score():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import score_pass_duration_fit, score_pass_timing_fit

    criteria = SearchCriteria()
    interval = _interval()
    first = _candidate(catalog_number=1, start_offset_minutes=-5.0, duration_minutes=4.0)
    second = _candidate(catalog_number=2, start_offset_minutes=-1.0, duration_minutes=4.0)

    assert score_pass_duration_fit(first, criteria, interval) == pytest.approx(
        score_pass_duration_fit(second, criteria, interval)
    )
    assert score_pass_timing_fit(first, criteria, interval) == pytest.approx(25.0)
    assert score_pass_timing_fit(second, criteria, interval) == pytest.approx(45.0)


def test_default_request_no_longer_gives_every_candidate_neutral_100_score():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import compute_match_score

    scored = compute_match_score(_candidate(duration_minutes=5.0), SearchCriteria(), _interval())

    assert scored.match_score == pytest.approx(75.0)
    assert scored.match_score != 100.0


def test_default_scoring_combines_duration_and_timing_deterministically():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import compute_match_score

    criteria = SearchCriteria()
    interval = _interval()

    first_score = compute_match_score(
        _candidate(start_offset_minutes=2.0, duration_minutes=6.0),
        criteria,
        interval,
    ).match_score
    second_score = compute_match_score(
        _candidate(start_offset_minutes=2.0, duration_minutes=6.0),
        criteria,
        interval,
    ).match_score

    assert first_score == pytest.approx((60.0 + 90.0) / 2.0)
    assert second_score == pytest.approx(first_score)


def test_duration_and_timing_both_influence_default_match_score():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import compute_match_score

    criteria = SearchCriteria()
    interval = _interval()

    short_score = compute_match_score(
        _candidate(start_offset_minutes=0.0, duration_minutes=2.0),
        criteria,
        interval,
    ).match_score
    long_score = compute_match_score(
        _candidate(start_offset_minutes=0.0, duration_minutes=8.0),
        criteria,
        interval,
    ).match_score
    early_score = compute_match_score(
        _candidate(start_offset_minutes=0.0, duration_minutes=5.0),
        criteria,
        interval,
    ).match_score
    later_score = compute_match_score(
        _candidate(start_offset_minutes=5.0, duration_minutes=5.0),
        criteria,
        interval,
    ).match_score

    assert long_score > short_score
    assert early_score > later_score


def test_enabled_preference_components_contribute_through_documented_scores_only():
    from tlefinder.core.models import (
        RangeConstraint,
        SearchCriteria,
        TargetToleranceConstraint,
    )
    from tlefinder.core.scoring import (
        compute_match_score,
        score_azimuth_fit,
        score_culmination_fit,
        score_pass_duration_fit,
        score_pass_timing_fit,
        score_sun_proximity_fit,
    )

    candidate = _candidate(
        duration_minutes=6.0,
        start_offset_minutes=2.0,
        culmination_altitude_deg=60.0,
        start_azimuth_deg=0.0,
        sun_proximity_deg=60.0,
    )
    criteria = SearchCriteria(
        culmination_altitude_target_deg=TargetToleranceConstraint(
            target=50.0,
            tolerance=20.0,
        ),
        start_azimuth_deg=TargetToleranceConstraint(target=350.0, tolerance=20.0),
        sun_proximity_deg=RangeConstraint(minimum=20.0, maximum=100.0),
    )
    interval = _interval()

    expected_components = [
        score_pass_duration_fit(candidate, criteria, interval),
        score_pass_timing_fit(candidate, criteria, interval),
        score_culmination_fit(candidate, criteria),
        score_azimuth_fit(candidate, criteria),
        score_sun_proximity_fit(candidate, criteria),
    ]

    assert compute_match_score(candidate, criteria, interval).match_score == pytest.approx(
        sum(expected_components) / len(expected_components)
    )


def test_official_score_is_independent_of_adapter_workflow_labels():
    from tlefinder.core.models import SearchCriteria
    from tlefinder.core.scoring import compute_match_score

    simple_candidate = _candidate()
    full_candidate = _candidate()
    simple_candidate.diagnostics["workflow_label"] = "simple_search"
    full_candidate.diagnostics["workflow_label"] = "full_search"

    assert compute_match_score(
        simple_candidate,
        SearchCriteria(),
        _interval(),
    ).match_score == pytest.approx(
        compute_match_score(
            full_candidate,
            SearchCriteria(),
            _interval(),
        ).match_score
    )
