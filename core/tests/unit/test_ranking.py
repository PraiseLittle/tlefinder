from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def _candidate(
    *,
    catalog_number: int,
    start_offset_minutes: int,
    match_score: float | None,
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
            end_time_utc=start_time + timedelta(minutes=5),
            culmination_time_utc=start_time + timedelta(minutes=2, seconds=30),
            start_azimuth_deg=270.0,
            end_azimuth_deg=90.0,
            culmination_azimuth_deg=180.0,
            culmination_altitude_deg=45.0,
        ),
        metrics=PassMetrics(satellite_altitude_km=420.0, sun_proximity_deg=25.0),
        match_score=match_score,
    )


def test_apply_score_threshold_keeps_candidates_at_or_above_threshold():
    from tlefinder.core.ranking import apply_score_threshold

    passing = _candidate(catalog_number=1, start_offset_minutes=0, match_score=70.0)
    boundary = _candidate(catalog_number=2, start_offset_minutes=1, match_score=60.0)
    failing = _candidate(catalog_number=3, start_offset_minutes=2, match_score=59.9)

    assert apply_score_threshold([passing, boundary, failing], 60.0) == [
        passing,
        boundary,
    ]


def test_apply_score_threshold_requires_populated_scores():
    from tlefinder.core.errors import SearchExecutionError
    from tlefinder.core.ranking import apply_score_threshold

    with pytest.raises(SearchExecutionError, match="match_score"):
        apply_score_threshold(
            [_candidate(catalog_number=1, start_offset_minutes=0, match_score=None)],
            0.0,
        )


def test_rank_candidates_orders_by_score_start_time_and_catalog_number():
    from tlefinder.core.ranking import rank_candidates

    best_score = _candidate(catalog_number=3, start_offset_minutes=10, match_score=95.0)
    later_tie = _candidate(catalog_number=1, start_offset_minutes=20, match_score=90.0)
    earlier_higher_catalog = _candidate(
        catalog_number=2,
        start_offset_minutes=5,
        match_score=90.0,
    )
    earlier_lower_catalog = _candidate(
        catalog_number=1,
        start_offset_minutes=5,
        match_score=90.0,
    )

    ranked = rank_candidates(
        [later_tie, earlier_higher_catalog, best_score, earlier_lower_catalog]
    )

    assert ranked == [
        best_score,
        earlier_lower_catalog,
        earlier_higher_catalog,
        later_tie,
    ]
    assert [candidate.rank for candidate in ranked] == [1, 2, 3, 4]


def test_rank_candidates_requires_populated_scores():
    from tlefinder.core.errors import SearchExecutionError
    from tlefinder.core.ranking import rank_candidates

    with pytest.raises(SearchExecutionError, match="match_score"):
        rank_candidates(
            [_candidate(catalog_number=1, start_offset_minutes=0, match_score=None)]
        )


def test_limit_results_truncates_ranked_candidates():
    from tlefinder.core.ranking import limit_results, rank_candidates

    ranked = rank_candidates(
        [
            _candidate(catalog_number=1, start_offset_minutes=0, match_score=90.0),
            _candidate(catalog_number=2, start_offset_minutes=1, match_score=80.0),
            _candidate(catalog_number=3, start_offset_minutes=2, match_score=70.0),
        ]
    )

    assert limit_results(ranked, 2) == ranked[:2]
