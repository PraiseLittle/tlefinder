from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _candidate(
    *,
    catalog_number: int = 25544,
    start_offset_minutes: int = 0,
    culmination_altitude_deg: float = 45.0,
    start_azimuth_deg: float = 270.0,
    end_azimuth_deg: float = 90.0,
    culmination_azimuth_deg: float = 180.0,
    sun_proximity_deg: float | None = 25.0,
    satellite_altitude_km: float = 420.0,
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
    catalog = f"{catalog_number:05d}"
    satellite = SatelliteRecord(
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
    return CandidatePass(
        satellite=satellite,
        geometry=PassGeometry(
            start_time_utc=start_time,
            end_time_utc=start_time + timedelta(minutes=5),
            culmination_time_utc=start_time + timedelta(minutes=2, seconds=30),
            start_azimuth_deg=start_azimuth_deg,
            end_azimuth_deg=end_azimuth_deg,
            culmination_azimuth_deg=culmination_azimuth_deg,
            culmination_altitude_deg=culmination_altitude_deg,
        ),
        metrics=PassMetrics(
            satellite_altitude_km=satellite_altitude_km,
            sun_proximity_deg=sun_proximity_deg,
        ),
    )


def test_culmination_filter_accepts_range_and_target_tolerance():
    from tlefinder.core.filtering import matches_culmination_constraints
    from tlefinder.core.models import (
        RangeConstraint,
        SearchCriteria,
        TargetToleranceConstraint,
    )

    criteria = SearchCriteria(
        culmination_altitude_deg=RangeConstraint(minimum=30.0, maximum=70.0),
        culmination_altitude_target_deg=TargetToleranceConstraint(
            target=50.0,
            tolerance=10.0,
        ),
    )

    assert matches_culmination_constraints(
        _candidate(culmination_altitude_deg=45.0),
        criteria,
    )
    assert not matches_culmination_constraints(
        _candidate(culmination_altitude_deg=25.0),
        criteria,
    )
    assert not matches_culmination_constraints(
        _candidate(culmination_altitude_deg=65.0),
        criteria,
    )


def test_azimuth_filter_uses_circular_wraparound_for_target_tolerance():
    from tlefinder.core.filtering import matches_azimuth_constraints
    from tlefinder.core.models import SearchCriteria, TargetToleranceConstraint

    criteria = SearchCriteria(
        start_azimuth_deg=TargetToleranceConstraint(target=350.0, tolerance=20.0)
    )

    assert matches_azimuth_constraints(_candidate(start_azimuth_deg=5.0), criteria)
    assert matches_azimuth_constraints(_candidate(start_azimuth_deg=330.0), criteria)
    assert not matches_azimuth_constraints(
        _candidate(start_azimuth_deg=329.9),
        criteria,
    )
    assert not matches_azimuth_constraints(
        _candidate(start_azimuth_deg=11.0),
        criteria,
    )


def test_azimuth_filter_checks_start_end_and_culmination_constraints():
    from tlefinder.core.filtering import matches_azimuth_constraints
    from tlefinder.core.models import SearchCriteria, TargetToleranceConstraint

    criteria = SearchCriteria(
        start_azimuth_deg=TargetToleranceConstraint(target=250.0, tolerance=30.0),
        end_azimuth_deg=TargetToleranceConstraint(target=90.0, tolerance=5.0),
        culmination_azimuth_deg=TargetToleranceConstraint(
            target=180.0,
            tolerance=10.0,
        ),
    )

    assert matches_azimuth_constraints(
        _candidate(
            start_azimuth_deg=230.0,
            end_azimuth_deg=95.0,
            culmination_azimuth_deg=171.0,
        ),
        criteria,
    )
    assert not matches_azimuth_constraints(
        _candidate(
            start_azimuth_deg=230.0,
            end_azimuth_deg=96.0,
            culmination_azimuth_deg=171.0,
        ),
        criteria,
    )


def test_sun_proximity_filter_requires_metric_when_constraint_is_enabled():
    from tlefinder.core.filtering import matches_sun_proximity_constraints
    from tlefinder.core.models import RangeConstraint, SearchCriteria

    criteria = SearchCriteria(
        sun_proximity_deg=RangeConstraint(minimum=15.0, maximum=30.0)
    )

    assert matches_sun_proximity_constraints(
        _candidate(sun_proximity_deg=20.0),
        criteria,
    )
    assert not matches_sun_proximity_constraints(
        _candidate(sun_proximity_deg=35.0),
        criteria,
    )
    assert not matches_sun_proximity_constraints(
        _candidate(sun_proximity_deg=None),
        criteria,
    )


def test_satellite_altitude_filter_applies_inclusive_range():
    from tlefinder.core.filtering import matches_satellite_altitude_constraints
    from tlefinder.core.models import RangeConstraint, SearchCriteria

    criteria = SearchCriteria(
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0)
    )

    assert matches_satellite_altitude_constraints(
        _candidate(satellite_altitude_km=400.0),
        criteria,
    )
    assert matches_satellite_altitude_constraints(
        _candidate(satellite_altitude_km=500.0),
        criteria,
    )
    assert not matches_satellite_altitude_constraints(
        _candidate(satellite_altitude_km=399.9),
        criteria,
    )


def test_filter_candidate_passes_keeps_matches_and_records_rejection_reasons():
    from tlefinder.core.filtering import filter_candidate_passes
    from tlefinder.core.models import RangeConstraint, SearchCriteria

    accepted = _candidate(catalog_number=1, culmination_altitude_deg=50.0)
    rejected = _candidate(catalog_number=2, culmination_altitude_deg=20.0)
    criteria = SearchCriteria(
        culmination_altitude_deg=RangeConstraint(minimum=30.0, maximum=70.0)
    )

    assert filter_candidate_passes([accepted, rejected], criteria) == [accepted]
    assert rejected.diagnostics["rejection_reasons"] == ["culmination_altitude"]


def test_geometry_filter_rejects_before_metric_dependent_constraints_are_needed():
    from tlefinder.core.filtering import filter_geometry_candidate_passes
    from tlefinder.core.models import PassMetrics, RangeConstraint, SearchCriteria

    accepted = _candidate(catalog_number=1, culmination_altitude_deg=50.0)
    rejected = _candidate(catalog_number=2, culmination_altitude_deg=20.0)
    accepted.metrics = PassMetrics(satellite_altitude_km=None, sun_proximity_deg=None)
    rejected.metrics = PassMetrics(satellite_altitude_km=None, sun_proximity_deg=None)
    criteria = SearchCriteria(
        culmination_altitude_deg=RangeConstraint(minimum=30.0, maximum=70.0),
        sun_proximity_deg=RangeConstraint(minimum=15.0, maximum=30.0),
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0),
    )

    assert filter_geometry_candidate_passes([accepted, rejected], criteria) == [accepted]
    assert rejected.diagnostics["rejection_reasons"] == ["culmination_altitude"]
    assert "rejection_reasons" not in accepted.diagnostics


def test_metric_filter_runs_after_required_metrics_are_available():
    from tlefinder.core.filtering import filter_metric_candidate_passes
    from tlefinder.core.models import PassMetrics, RangeConstraint, SearchCriteria

    accepted = _candidate(catalog_number=1)
    rejected = _candidate(catalog_number=2)
    accepted.metrics = PassMetrics(satellite_altitude_km=420.0, sun_proximity_deg=20.0)
    rejected.metrics = PassMetrics(satellite_altitude_km=420.0, sun_proximity_deg=35.0)
    missing_metric = _candidate(catalog_number=3)
    missing_metric.metrics = PassMetrics(
        satellite_altitude_km=None,
        sun_proximity_deg=None,
    )
    criteria = SearchCriteria(
        sun_proximity_deg=RangeConstraint(minimum=15.0, maximum=30.0),
        satellite_altitude_km=RangeConstraint(minimum=400.0, maximum=500.0),
    )

    assert filter_metric_candidate_passes(
        [accepted, rejected, missing_metric],
        criteria,
    ) == [accepted]
    assert rejected.diagnostics["rejection_reasons"] == ["sun_proximity"]
    assert missing_metric.diagnostics["rejection_reasons"] == [
        "sun_proximity",
        "satellite_altitude",
    ]
