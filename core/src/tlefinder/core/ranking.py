"""Thresholding, deterministic ordering, and result limiting."""

from __future__ import annotations

from tlefinder.core.errors import SearchExecutionError
from tlefinder.core.models import CandidatePass


def apply_score_threshold(
    candidates: list[CandidatePass],
    threshold: float,
) -> list[CandidatePass]:
    """Return candidates with populated scores at or above ``threshold``."""

    return [
        candidate
        for candidate in candidates
        if _require_match_score(candidate) >= threshold
    ]


def rank_candidates(candidates: list[CandidatePass]) -> list[CandidatePass]:
    """Sort candidates by score, start time, then catalog number and set rank."""

    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -_require_match_score(candidate),
            candidate.geometry.start_time_utc,
            candidate.satellite.tle.catalog_number,
        ),
    )
    for index, candidate in enumerate(ranked, start=1):
        candidate.rank = index
    return ranked


def limit_results(candidates: list[CandidatePass], limit: int) -> list[CandidatePass]:
    """Return at most ``limit`` ranked candidates."""

    return candidates[:limit]


def _require_match_score(candidate: CandidatePass) -> float:
    if candidate.match_score is None:
        raise SearchExecutionError(
            "candidate match_score must be populated before ranking"
        )
    return float(candidate.match_score)


__all__ = [
    "apply_score_threshold",
    "limit_results",
    "rank_candidates",
]
