"""Typed exceptions raised by the reusable core."""

from __future__ import annotations


class TleFinderError(Exception):
    """Base class for expected TLE Finder core failures."""


class ValidationError(TleFinderError, ValueError):
    """Raised when a search request violates the core contract."""


class TleFreshnessError(TleFinderError):
    """Raised when no TLE dataset satisfies freshness requirements."""


class TleLoadError(TleFinderError):
    """Raised when TLE retrieval or parsing fails."""


class PropagationError(TleFinderError):
    """Raised when orbital propagation cannot complete."""


class SearchExecutionError(TleFinderError):
    """Raised for engine-level failures without a narrower error type."""


__all__ = [
    "PropagationError",
    "SearchExecutionError",
    "TleFinderError",
    "TleFreshnessError",
    "TleLoadError",
    "ValidationError",
]
