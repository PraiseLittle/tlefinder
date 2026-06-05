"""Skyfield-based pass detection and metric computation."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import acos, asin, atan2, cos, degrees, floor, isfinite, radians, sin, tan
import os
from typing import Any, Callable

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

from tlefinder.core.errors import PropagationError
from tlefinder.core.models import (
    CandidatePass,
    GroundStation,
    PassGeometry,
    PassMetrics,
    SatelliteRecord,
)

PASS_HORIZON_DEGREES = 10.0
PASS_SAMPLE_COUNT = 49
EVENT_SEARCH_LOOKAROUND_WINDOW_MULTIPLIER = 6
EVENT_SEARCH_MIN_LOOKAROUND = timedelta(minutes=15)
EVENT_SEARCH_MAX_LOOKAROUND = timedelta(hours=6)
EVENT_SEARCH_FALLBACK_LOOKAROUND_MULTIPLIER = 2
EVENT_REFINEMENT_BRACKET = timedelta(seconds=1)
EVENT_REFINEMENT_MAX_BRACKET = timedelta(minutes=2)
CULMINATION_REFINEMENT_SAMPLE_OFFSET = timedelta(seconds=0.25)
# Preserve the established Skyfield event-time convention after local refinement.
CULMINATION_COMPATIBILITY_BIAS = timedelta(seconds=0.0158)
PARALLEL_SEARCH_BACKEND_PROCESS_POOL = "process_pool"
SUPPORTED_PARALLEL_BACKENDS = frozenset({PARALLEL_SEARCH_BACKEND_PROCESS_POOL})
DEFAULT_PARALLEL_WORKER_COUNT = 4
DEFAULT_PARALLEL_CHUNK_SIZE = 32
MAX_PARALLEL_WORKERS = 16
MAX_PARALLEL_CHUNK_SIZE = 4096
MAX_SKIPPED_RECORD_DIAGNOSTICS = 20
_PROCESS_POOL_EXECUTOR = ProcessPoolExecutor


@dataclass(frozen=True, slots=True)
class PassAnalysisResult:
    """Candidate passes plus JSON-friendly work diagnostics."""

    candidates: list[CandidatePass]
    diagnostics: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParallelSearchConfig:
    """Internal contract for future parallel pass-geometry execution."""

    enabled: bool = False
    requested_worker_count: int = 1
    chunk_size: int = DEFAULT_PARALLEL_CHUNK_SIZE
    backend_name: str = PARALLEL_SEARCH_BACKEND_PROCESS_POOL
    fallback_reason: str | None = None
    effective_worker_count: int = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise PropagationError("enabled must be a boolean")

        requested_worker_count = _validate_positive_int(
            self.requested_worker_count,
            name="requested_worker_count",
        )
        if requested_worker_count > MAX_PARALLEL_WORKERS:
            raise PropagationError(
                f"requested_worker_count must be <= {MAX_PARALLEL_WORKERS}"
            )

        chunk_size = _validate_positive_int(self.chunk_size, name="chunk_size")
        if chunk_size > MAX_PARALLEL_CHUNK_SIZE:
            raise PropagationError(f"chunk_size must be <= {MAX_PARALLEL_CHUNK_SIZE}")

        if not isinstance(self.backend_name, str):
            raise PropagationError("backend_name must be one of: process_pool")
        backend_name = self.backend_name.strip()
        if backend_name not in SUPPORTED_PARALLEL_BACKENDS:
            supported = ", ".join(sorted(SUPPORTED_PARALLEL_BACKENDS))
            raise PropagationError(f"backend_name must be one of: {supported}")

        fallback_reason = self.fallback_reason
        if fallback_reason is not None and not isinstance(fallback_reason, str):
            raise PropagationError("fallback_reason must be a string")

        enabled = self.enabled
        if enabled and requested_worker_count == 1 and fallback_reason is None:
            fallback_reason = "single_worker"

        if fallback_reason is not None:
            enabled = False
            effective_worker_count = 1
        elif enabled:
            effective_worker_count = requested_worker_count
        else:
            effective_worker_count = 1

        object.__setattr__(self, "enabled", enabled)
        object.__setattr__(
            self,
            "requested_worker_count",
            requested_worker_count,
        )
        object.__setattr__(self, "chunk_size", chunk_size)
        object.__setattr__(self, "backend_name", backend_name)
        object.__setattr__(self, "fallback_reason", fallback_reason)
        object.__setattr__(
            self,
            "effective_worker_count",
            effective_worker_count,
        )


@dataclass(frozen=True, slots=True)
class _ParallelGeometryChunkInput:
    """Serializable pass-geometry worker input."""

    chunk_index: int
    start_record_index: int
    records: list[SatelliteRecord]
    station: GroundStation
    interval: tuple[datetime, datetime]


@dataclass(frozen=True, slots=True)
class _ParallelGeometryChunkResult:
    """Serializable pass-geometry worker output."""

    chunk_index: int
    start_record_index: int
    record_count: int
    processed_satellite_count: int
    candidates: list[CandidatePass]
    skipped_diagnostics: list[dict[str, Any]]
    event_search_span: dict[str, str]


def derive_default_parallel_search_config(
    *,
    enabled: bool = True,
    cpu_count: int | None = None,
    requested_worker_count: int | None = None,
    chunk_size: int | None = None,
    backend_name: str = PARALLEL_SEARCH_BACKEND_PROCESS_POOL,
) -> ParallelSearchConfig:
    """Return the conservative default process-pool configuration.

    Defaults are local policy only: deriving them does not inspect TLE sources,
    touch the network, or depend on live benchmark data.
    """

    worker_count = (
        _default_parallel_worker_count(cpu_count)
        if requested_worker_count is None
        else requested_worker_count
    )
    return ParallelSearchConfig(
        enabled=enabled,
        requested_worker_count=worker_count,
        chunk_size=DEFAULT_PARALLEL_CHUNK_SIZE if chunk_size is None else chunk_size,
        backend_name=backend_name,
    )


class PassAnalysisSession:
    """Per-search Skyfield object cache and pass-analysis operations."""

    def __init__(
        self,
        station: GroundStation,
        interval: tuple[datetime, datetime],
    ) -> None:
        self.station = station
        self.interval = _validate_interval(interval)
        self._observer = _build_observer(station)
        self._satellites: dict[tuple[str, str, str], EarthSatellite] = {}
        self._alt_az_cache: dict[
            tuple[tuple[str, str, str], datetime],
            tuple[float, float],
        ] = {}

    def find_candidate_geometries_with_diagnostics(
        self,
        records: list[SatelliteRecord],
        *,
        candidate_budget: int | None = None,
        parallel_search: ParallelSearchConfig | None = None,
    ) -> PassAnalysisResult:
        """Propagate records and return geometry-only candidate passes."""

        parallel_config = _normalize_parallel_search_config(parallel_search)
        if parallel_config is not None and parallel_config.enabled:
            parallel_config = _parallel_runtime_config(
                parallel_config,
                record_count=len(records),
            )

        if parallel_config is not None and parallel_config.enabled:
            return _with_parallel_search_diagnostics(
                _find_candidate_geometries_with_parallel_boundary(
                    records,
                    self.station,
                    self.interval,
                    candidate_budget=candidate_budget,
                    parallel_search=parallel_config,
                ),
                parallel_search=parallel_config,
                record_count=len(records),
            )

        normalized_candidate_budget = _normalize_candidate_budget(candidate_budget)
        candidates: list[CandidatePass] = []
        skipped_diagnostics: list[dict[str, Any]] = []
        inspected_records: list[SatelliteRecord] = []
        budget_reached = False

        for record in records:
            if (
                normalized_candidate_budget is not None
                and len(candidates) >= normalized_candidate_budget
            ):
                budget_reached = True
                break

            inspected_records.append(record)

            def record_alt_az(
                event_time: datetime,
                alt_az: tuple[float, float],
                *,
                record: SatelliteRecord = record,
            ) -> None:
                self._record_alt_az(record, event_time, alt_az)

            geometry, diagnostics = _compute_pass_geometry_with_context(
                record,
                self.interval,
                self._satellite_for(record),
                self._observer,
                alt_az_recorder=record_alt_az,
            )
            if geometry is None:
                skipped_diagnostics.append(_satellite_diagnostics(record, diagnostics))
                continue

            candidates.append(
                CandidatePass(
                    satellite=record,
                    geometry=geometry,
                    metrics=PassMetrics(),
                    diagnostics=diagnostics,
                )
            )

        result = PassAnalysisResult(
            candidates=candidates,
            diagnostics=_with_candidate_budget_diagnostics(
                _pass_analysis_diagnostics(
                    inspected_records,
                    candidates,
                    skipped_diagnostics,
                    self.interval,
                ),
                candidate_budget=normalized_candidate_budget,
                budget_reached=budget_reached,
                processed_satellite_count=len(inspected_records),
                total_satellite_count=len(records),
                processed_candidate_count=len(candidates),
            ),
        )
        if parallel_config is not None:
            return _with_parallel_search_diagnostics(
                result,
                parallel_search=parallel_config,
                record_count=len(records),
            )
        return result

    def compute_required_metrics(
        self,
        candidates: list[CandidatePass],
        *,
        include_satellite_altitude: bool,
        include_sun_proximity: bool,
    ) -> list[CandidatePass]:
        """Populate requested metrics for candidates, preserving existing values."""

        for candidate in candidates:
            _validate_geometry(candidate.geometry)
            satellite = self._satellite_for(candidate.satellite)
            satellite_altitude_km = candidate.metrics.satellite_altitude_km
            sun_proximity_deg = candidate.metrics.sun_proximity_deg

            if include_satellite_altitude and satellite_altitude_km is None:
                satellite_altitude_km = _compute_mean_satellite_altitude_km(
                    satellite,
                    candidate.geometry,
                )
            if include_sun_proximity and sun_proximity_deg is None:
                satellite_key = _satellite_cache_key(candidate.satellite)
                sun_proximity_deg = _compute_sun_proximity_from_context(
                    candidate,
                    self.station,
                    satellite,
                    self._observer,
                    alt_az_lookup=lambda event_time, satellite_key=satellite_key: (
                        self._alt_az_cache.get((satellite_key, event_time))
                    ),
                )

            candidate.metrics = PassMetrics(
                satellite_altitude_km=satellite_altitude_km,
                sun_proximity_deg=sun_proximity_deg,
            )

        return candidates

    def _satellite_for(self, record: SatelliteRecord) -> EarthSatellite:
        key = _satellite_cache_key(record)
        satellite = self._satellites.get(key)
        if satellite is None:
            satellite = _build_satellite(record)
            self._satellites[key] = satellite
        return satellite

    def _record_alt_az(
        self,
        record: SatelliteRecord,
        event_time: datetime,
        alt_az: tuple[float, float],
    ) -> None:
        self._alt_az_cache[(_satellite_cache_key(record), event_time)] = alt_az


def create_pass_analysis_session(
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> PassAnalysisSession:
    """Create an opaque per-search pass-analysis session."""

    return PassAnalysisSession(station, interval)


def find_candidate_passes(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> list[CandidatePass]:
    """Propagate satellite records and return detected candidate passes."""

    result = find_candidate_passes_with_diagnostics(records, station, interval)
    return result.candidates


def find_candidate_passes_with_diagnostics(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> PassAnalysisResult:
    """Propagate records and return candidates with pass-analysis diagnostics."""

    session = create_pass_analysis_session(station, interval)
    result = session.find_candidate_geometries_with_diagnostics(records)
    session.compute_required_metrics(
        result.candidates,
        include_satellite_altitude=True,
        include_sun_proximity=True,
    )
    return result


def find_candidate_geometries_with_diagnostics(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
    *,
    candidate_budget: int | None = None,
    parallel_search: ParallelSearchConfig | None = None,
) -> PassAnalysisResult:
    """Propagate records and return candidate geometries without pass metrics."""

    parallel_config = _normalize_parallel_search_config(parallel_search)
    if parallel_config is not None and parallel_config.enabled:
        parallel_config = _parallel_runtime_config(
            parallel_config,
            record_count=len(records),
        )

    if parallel_config is not None and parallel_config.enabled:
        return _with_parallel_search_diagnostics(
            _find_candidate_geometries_with_parallel_boundary(
                records,
                station,
                interval,
                candidate_budget=candidate_budget,
                parallel_search=parallel_config,
            ),
            parallel_search=parallel_config,
            record_count=len(records),
        )

    session = create_pass_analysis_session(station, interval)
    return session.find_candidate_geometries_with_diagnostics(
        records,
        candidate_budget=candidate_budget,
        parallel_search=parallel_config,
    )


def _find_candidate_geometries_with_parallel_boundary(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
    *,
    candidate_budget: int | None,
    parallel_search: ParallelSearchConfig,
) -> PassAnalysisResult:
    """Execute pass geometry in process-pool workers using bounded chunk waves."""

    normalized_candidate_budget = _normalize_candidate_budget(candidate_budget)
    chunk_inputs = _parallel_geometry_chunk_inputs(
        records,
        station,
        interval,
        chunk_size=parallel_search.chunk_size,
    )
    chunk_results: list[_ParallelGeometryChunkResult] = []
    budget_reached = False
    executor: Any | None = None
    try:
        executor = _PROCESS_POOL_EXECUTOR(
            max_workers=parallel_search.effective_worker_count
        )
        chunk_waves = _parallel_geometry_chunk_waves(
            chunk_inputs,
            wave_size=parallel_search.effective_worker_count,
        )
        for wave_index, wave_inputs in enumerate(chunk_waves):
            chunk_results.extend(
                executor.map(_find_candidate_geometries_worker, wave_inputs)
            )
            if normalized_candidate_budget is None:
                continue
            merged_wave_result = _merge_parallel_geometry_chunk_results(
                records,
                interval,
                chunk_results,
            )
            if len(merged_wave_result.candidates) >= normalized_candidate_budget:
                budget_reached = wave_index < len(chunk_waves) - 1
                break
    except Exception as exc:
        raise PropagationError("parallel pass geometry worker failed") from exc
    finally:
        if executor is not None:
            _shutdown_parallel_executor(executor)

    result = _merge_parallel_geometry_chunk_results(
        records,
        interval,
        chunk_results,
    )
    return PassAnalysisResult(
        candidates=result.candidates,
        diagnostics=_with_candidate_budget_diagnostics(
            result.diagnostics,
            candidate_budget=normalized_candidate_budget,
            budget_reached=budget_reached,
            processed_satellite_count=_processed_satellite_count_from_chunk_results(
                chunk_results
            ),
            total_satellite_count=len(records),
            processed_candidate_count=len(result.candidates),
        ),
    )


def _find_candidate_geometries_worker(
    chunk_input: _ParallelGeometryChunkInput,
) -> _ParallelGeometryChunkResult:
    """Run exact pass geometry for one chunk inside a worker process."""

    session = PassAnalysisSession(chunk_input.station, chunk_input.interval)
    result = session.find_candidate_geometries_with_diagnostics(chunk_input.records)
    processed_satellite_count = _diagnostic_int(
        result.diagnostics,
        "processed_satellite_count",
        default=_diagnostic_int(
            result.diagnostics,
            "satellite_records_inspected",
            default=len(chunk_input.records),
        ),
    )
    return _ParallelGeometryChunkResult(
        chunk_index=chunk_input.chunk_index,
        start_record_index=chunk_input.start_record_index,
        record_count=len(chunk_input.records),
        processed_satellite_count=processed_satellite_count,
        candidates=result.candidates,
        skipped_diagnostics=_json_friendly_diagnostics_list(
            result.diagnostics.get("skipped_records", [])
        ),
        event_search_span=_json_friendly_string_dict(
            result.diagnostics.get("event_search_span", {})
        ),
    )


def _merge_parallel_geometry_chunk_results(
    records: list[SatelliteRecord],
    interval: tuple[datetime, datetime],
    chunk_results: list[_ParallelGeometryChunkResult],
) -> PassAnalysisResult:
    ordered_results = sorted(
        chunk_results,
        key=lambda result: (result.start_record_index, result.chunk_index),
    )
    candidates: list[CandidatePass] = []
    skipped_diagnostics: list[dict[str, Any]] = []
    inspected_records: list[SatelliteRecord] = []

    for chunk_result in ordered_results:
        processed_satellite_count = max(
            0,
            min(chunk_result.processed_satellite_count, chunk_result.record_count),
        )
        inspected_records.extend(
            records[
                chunk_result.start_record_index : (
                    chunk_result.start_record_index + processed_satellite_count
                )
            ]
        )
        candidates.extend(chunk_result.candidates)
        skipped_diagnostics.extend(chunk_result.skipped_diagnostics)

    return PassAnalysisResult(
        candidates=candidates,
        diagnostics=_pass_analysis_diagnostics(
            inspected_records,
            candidates,
            skipped_diagnostics,
            interval,
        ),
    )


def _find_candidate_passes_with_diagnostics(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> tuple[list[CandidatePass], list[dict[str, Any]]]:
    result = find_candidate_passes_with_diagnostics(
        records,
        station,
        interval,
    )
    return result.candidates, result.diagnostics["skipped_records"]


def _satellite_diagnostics(
    record: SatelliteRecord,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "satellite_name": record.tle.name,
        "catalog_number": record.tle.catalog_number,
        **diagnostics,
    }


def _pass_analysis_diagnostics(
    records: list[SatelliteRecord],
    candidates: list[CandidatePass],
    skipped_diagnostics: list[dict[str, Any]],
    interval: tuple[datetime, datetime],
) -> dict[str, Any]:
    event_search_span = _aggregate_event_search_span(
        [
            *(
                candidate.diagnostics.get("event_search_span")
                for candidate in candidates
            ),
            *(
                diagnostics.get("event_search_span")
                for diagnostics in skipped_diagnostics
            ),
        ],
        interval,
    )
    bounded_skipped_diagnostics = _bounded_skipped_record_diagnostics(
        skipped_diagnostics,
    )
    diagnostics: dict[str, Any] = {
        "satellite_records_inspected": len(records),
        "candidate_geometries_found": len(candidates),
        "skipped_record_count": len(skipped_diagnostics),
        "skipped_records": bounded_skipped_diagnostics,
        "event_search_span": event_search_span,
    }
    omitted_count = len(skipped_diagnostics) - len(bounded_skipped_diagnostics)
    if omitted_count > 0:
        diagnostics["skipped_records_truncated"] = True
        diagnostics["skipped_records_omitted"] = omitted_count
    return diagnostics


def _with_candidate_budget_diagnostics(
    diagnostics: dict[str, Any],
    *,
    candidate_budget: int | None,
    budget_reached: bool,
    processed_satellite_count: int,
    total_satellite_count: int,
    processed_candidate_count: int,
) -> dict[str, Any]:
    if candidate_budget is None:
        return diagnostics

    return {
        **diagnostics,
        "candidate_budget": candidate_budget,
        "budget_reached": budget_reached,
        "processed_satellite_count": processed_satellite_count,
        "unprocessed_satellite_count": max(
            0,
            total_satellite_count - processed_satellite_count,
        ),
        "processed_candidate_count": processed_candidate_count,
    }


def _with_parallel_search_diagnostics(
    result: PassAnalysisResult,
    *,
    parallel_search: ParallelSearchConfig,
    record_count: int,
) -> PassAnalysisResult:
    return PassAnalysisResult(
        candidates=result.candidates,
        diagnostics={
            **result.diagnostics,
            "parallel_search": _parallel_search_diagnostics(
                parallel_search,
                record_count=record_count,
            ),
        },
    )


def _parallel_search_diagnostics(
    parallel_search: ParallelSearchConfig,
    *,
    record_count: int,
) -> dict[str, Any]:
    if parallel_search.enabled:
        chunk_count = _chunk_count(record_count, parallel_search.chunk_size)
    else:
        chunk_count = 1 if record_count else 0

    diagnostics: dict[str, Any] = {
        "enabled": parallel_search.enabled,
        "backend": parallel_search.backend_name,
        "requested_workers": parallel_search.requested_worker_count,
        "effective_workers": parallel_search.effective_worker_count,
        "chunk_size": parallel_search.chunk_size,
        "chunk_count": chunk_count,
    }
    if parallel_search.fallback_reason is not None:
        diagnostics["fallback_reason"] = parallel_search.fallback_reason
    return diagnostics


def _shutdown_parallel_executor(executor: Any) -> None:
    shutdown = getattr(executor, "shutdown", None)
    if not callable(shutdown):
        return
    try:
        shutdown(wait=True, cancel_futures=True)
    except TypeError:
        shutdown(wait=True)


def _bounded_skipped_record_diagnostics(
    skipped_diagnostics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        dict(diagnostics)
        for diagnostics in skipped_diagnostics[:MAX_SKIPPED_RECORD_DIAGNOSTICS]
    ]


def _normalize_parallel_search_config(
    parallel_search: ParallelSearchConfig | None,
) -> ParallelSearchConfig | None:
    if parallel_search is None:
        return None
    if not isinstance(parallel_search, ParallelSearchConfig):
        raise PropagationError("parallel_search must be a ParallelSearchConfig")
    return parallel_search


def _parallel_runtime_config(
    parallel_search: ParallelSearchConfig,
    *,
    record_count: int,
) -> ParallelSearchConfig:
    if not parallel_search.enabled:
        return parallel_search

    fallback_reason: str | None = None
    if record_count == 0:
        fallback_reason = "empty_records"
    elif _chunk_count(record_count, parallel_search.chunk_size) <= 1:
        fallback_reason = "small_record_set"
    elif not _process_pool_backend_supported():
        fallback_reason = "unsupported_platform"

    if fallback_reason is None:
        return parallel_search

    return ParallelSearchConfig(
        enabled=True,
        requested_worker_count=parallel_search.requested_worker_count,
        chunk_size=parallel_search.chunk_size,
        backend_name=parallel_search.backend_name,
        fallback_reason=fallback_reason,
    )


def _process_pool_backend_supported() -> bool:
    return True


def _default_parallel_worker_count(cpu_count: int | None) -> int:
    detected_count = os.cpu_count() if cpu_count is None else cpu_count
    if isinstance(detected_count, bool) or not isinstance(detected_count, int):
        detected_count = 1
    if detected_count <= 0:
        detected_count = 1
    return max(
        1,
        min(DEFAULT_PARALLEL_WORKER_COUNT, detected_count, MAX_PARALLEL_WORKERS),
    )


def _parallel_geometry_chunk_inputs(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
    *,
    chunk_size: int,
) -> list[_ParallelGeometryChunkInput]:
    return [
        _ParallelGeometryChunkInput(
            chunk_index=chunk_index,
            start_record_index=start_record_index,
            records=records[start_record_index : start_record_index + chunk_size],
            station=station,
            interval=interval,
        )
        for chunk_index, start_record_index in enumerate(
            range(0, len(records), chunk_size)
        )
    ]


def _parallel_geometry_chunk_waves(
    chunk_inputs: list[_ParallelGeometryChunkInput],
    *,
    wave_size: int,
) -> list[list[_ParallelGeometryChunkInput]]:
    return [
        chunk_inputs[index : index + wave_size]
        for index in range(0, len(chunk_inputs), wave_size)
    ]


def _processed_satellite_count_from_chunk_results(
    chunk_results: list[_ParallelGeometryChunkResult],
) -> int:
    return sum(
        max(0, min(chunk_result.processed_satellite_count, chunk_result.record_count))
        for chunk_result in chunk_results
    )


def _satellite_record_chunks(
    records: list[SatelliteRecord],
    chunk_size: int,
) -> list[list[SatelliteRecord]]:
    return [
        records[index : index + chunk_size]
        for index in range(0, len(records), chunk_size)
    ]


def _chunk_count(record_count: int, chunk_size: int) -> int:
    if record_count <= 0:
        return 0
    return (record_count + chunk_size - 1) // chunk_size


def _diagnostic_int(
    diagnostics: dict[str, Any],
    key: str,
    *,
    default: int,
) -> int:
    value = diagnostics.get(key, default)
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_friendly_diagnostics_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _json_friendly_string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, str)
    }


def _normalize_candidate_budget(candidate_budget: int | None) -> int | None:
    if candidate_budget is None:
        return None
    if isinstance(candidate_budget, bool) or not isinstance(candidate_budget, int):
        raise PropagationError("candidate_budget must be a positive integer")
    if candidate_budget <= 0:
        raise PropagationError("candidate_budget must be a positive integer")
    return candidate_budget


def _validate_positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PropagationError(f"{name} must be a positive integer")
    if value <= 0:
        raise PropagationError(f"{name} must be a positive integer")
    return value


def compute_pass_geometry(
    record: SatelliteRecord,
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> PassGeometry | None:
    """Compute pass rise, culmination, and end geometry for one satellite."""

    geometry, _ = _compute_pass_geometry_with_diagnostics(record, station, interval)
    return geometry


def compute_pass_metrics(
    candidate: CandidatePass,
    station: GroundStation,
) -> PassMetrics:
    """Compute pass-level metrics used by later filtering and scoring stages."""

    _validate_geometry(candidate.geometry)
    satellite = _build_satellite(candidate.satellite)
    observer = _build_observer(station)

    return PassMetrics(
        satellite_altitude_km=_compute_mean_satellite_altitude_km(
            satellite,
            candidate.geometry,
        ),
        sun_proximity_deg=_compute_sun_proximity_from_context(
            candidate,
            station,
            satellite,
            observer,
        ),
    )


def compute_satellite_altitude_km(
    record: SatelliteRecord,
    event_time: datetime,
) -> float:
    """Compute satellite altitude above the WGS84 Earth surface."""

    satellite = _build_satellite(record)
    return _compute_satellite_altitude_km_from_satellite(satellite, event_time)


def compute_alt_az(
    record: SatelliteRecord,
    station: GroundStation,
    event_time: datetime,
) -> tuple[float, float]:
    """Compute topocentric apparent altitude and azimuth for one instant."""

    satellite = _build_satellite(record)
    observer = _build_observer(station)
    return _compute_alt_az_from_satellite(satellite, observer, event_time)


def compute_sun_proximity(
    candidate: CandidatePass,
    station: GroundStation,
) -> float | None:
    """Compute the closest angular separation from the Sun over the pass."""

    _validate_geometry(candidate.geometry)
    satellite = _build_satellite(candidate.satellite)
    observer = _build_observer(station)
    return _compute_sun_proximity_from_context(
        candidate,
        station,
        satellite,
        observer,
    )


def _compute_mean_satellite_altitude_km(
    satellite: EarthSatellite,
    geometry: PassGeometry,
) -> float:
    sample_times = _sample_datetimes(
        geometry.start_time_utc,
        geometry.end_time_utc,
    )
    altitudes = [
        _compute_satellite_altitude_km_from_satellite(satellite, sample_time)
        for sample_time in sample_times
    ]
    return float(np.mean(altitudes))


def _compute_sun_proximity_from_context(
    candidate: CandidatePass,
    station: GroundStation,
    satellite: EarthSatellite,
    observer: Any,
    *,
    alt_az_lookup: Callable[[datetime], tuple[float, float] | None] | None = None,
) -> float | None:
    separations: list[float] = []

    for sample_time in _sample_datetimes(
        candidate.geometry.start_time_utc,
        candidate.geometry.end_time_utc,
    ):
        cached_alt_az = None if alt_az_lookup is None else alt_az_lookup(sample_time)
        if cached_alt_az is None:
            satellite_altitude_deg, satellite_azimuth_deg = (
                _compute_alt_az_from_satellite(
                    satellite,
                    observer,
                    sample_time,
                )
            )
        else:
            satellite_altitude_deg, satellite_azimuth_deg = cached_alt_az
        sun_altitude_deg, sun_azimuth_deg = _compute_sun_alt_az(station, sample_time)
        separations.append(
            _angular_separation_deg(
                satellite_altitude_deg,
                satellite_azimuth_deg,
                sun_altitude_deg,
                sun_azimuth_deg,
            )
        )

    if not separations:
        return None
    return min(separations)


def _compute_pass_geometry_with_diagnostics(
    record: SatelliteRecord,
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> tuple[PassGeometry | None, dict[str, Any]]:
    start_utc, end_utc = _validate_interval(interval)
    return _compute_pass_geometry_with_context(
        record,
        (start_utc, end_utc),
        _build_satellite(record),
        _build_observer(station),
    )


def _compute_pass_geometry_with_context(
    record: SatelliteRecord,
    interval: tuple[datetime, datetime],
    satellite: EarthSatellite,
    observer: Any,
    *,
    alt_az_recorder: Callable[[datetime, tuple[float, float]], None] | None = None,
) -> tuple[PassGeometry | None, dict[str, Any]]:
    start_utc, end_utc = _validate_interval(interval)
    event_search_spans = [
        _event_search_span_diagnostics(
            start_utc,
            end_utc,
            include_previous_day=False,
        )
    ]
    events = _find_events_for_interval(
        satellite,
        observer,
        start_utc,
        end_utc,
    )
    pass_events = _select_pass_events(events, start_utc, end_utc)
    used_event_search_fallback = False

    if _needs_event_search_fallback(
        pass_events,
    ):
        used_event_search_fallback = True
        event_search_spans.append(
            _event_search_span_diagnostics(
                start_utc,
                end_utc,
                include_previous_day=True,
            )
        )
        fallback_events = _find_events_for_interval(
            satellite,
            observer,
            start_utc,
            end_utc,
            include_previous_day=True,
        )
        fallback_pass_events = _select_pass_events(
            fallback_events,
            start_utc,
            end_utc,
        )
        events = fallback_events
        if fallback_pass_events is not None:
            pass_events = fallback_pass_events

    events_inside_window = [
        event_code
        for event_code, event_time in events
        if _skyfield_time_inside_interval(event_time, start_utc, end_utc)
    ]
    diagnostics: dict[str, Any] = {
        "event_count": len(events_inside_window),
        "event_sequence": events_inside_window,
        "partial_window": False,
        "event_search_span": _aggregate_diagnostic_spans(event_search_spans),
        "used_event_search_fallback": used_event_search_fallback,
    }

    if pass_events is None:
        diagnostics["skipped_reason"] = "no_rise_culmination_pair"
        return None, diagnostics

    pass_events = _refine_pass_events_with_local_geometry(
        satellite,
        observer,
        pass_events,
    )

    start_time = pass_events.get("start")
    culmination_time = pass_events.get("culmination")
    end_time = pass_events.get("end")

    if culmination_time is None:
        diagnostics["skipped_reason"] = "missing_culmination"
        return None, diagnostics

    start_source = (
        "observed"
        if start_time is not None
        and _skyfield_time_inside_interval(start_time, start_utc, end_utc)
        else "extended_search"
    )
    end_source = (
        "observed"
        if end_time is not None
        and _skyfield_time_inside_interval(end_time, start_utc, end_utc)
        else "extended_search"
    )

    if start_time is None:
        if end_time is None:
            diagnostics["skipped_reason"] = "missing_start_and_end"
            return None, diagnostics
        start_time = culmination_time - (end_time - culmination_time)
        start_source = "estimated"
        diagnostics["partial_window"] = True

    if end_time is None:
        end_time = start_time + (culmination_time - start_time) * 2.0
        end_source = "estimated"
        diagnostics["partial_window"] = True

    start_time_utc = _skyfield_time_to_datetime(start_time)
    culmination_time_utc = _skyfield_time_to_datetime(culmination_time)
    end_time_utc = _skyfield_time_to_datetime(end_time)

    if start_time_utc < start_utc or end_time_utc > end_utc:
        diagnostics["partial_window"] = True

    diagnostics["start_time_source"] = start_source
    diagnostics["end_time_source"] = end_source

    start_altitude_deg, start_azimuth_deg = _compute_alt_az_from_satellite(
        satellite,
        observer,
        start_time_utc,
    )
    culmination_altitude_deg, culmination_azimuth_deg = _compute_alt_az_from_satellite(
        satellite,
        observer,
        culmination_time_utc,
    )
    end_altitude_deg, end_azimuth_deg = _compute_alt_az_from_satellite(
        satellite,
        observer,
        end_time_utc,
    )
    if alt_az_recorder is not None:
        alt_az_recorder(start_time_utc, (start_altitude_deg, start_azimuth_deg))
        alt_az_recorder(
            culmination_time_utc,
            (culmination_altitude_deg, culmination_azimuth_deg),
        )
        alt_az_recorder(end_time_utc, (end_altitude_deg, end_azimuth_deg))

    return (
        PassGeometry(
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            culmination_time_utc=culmination_time_utc,
            start_azimuth_deg=start_azimuth_deg,
            end_azimuth_deg=end_azimuth_deg,
            culmination_azimuth_deg=culmination_azimuth_deg,
            culmination_altitude_deg=culmination_altitude_deg,
        ),
        diagnostics,
    )


def _select_pass_events(
    events: list[tuple[int, Any]],
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    completed: list[dict[str, Any]] = []

    for event_code, event_time in events:
        if event_code == 0:
            if active and active.get("culmination") is not None:
                completed.append(active)
            active = {"start": event_time}
        elif event_code == 1:
            if active is None:
                active = {}
            active["culmination"] = event_time
        elif event_code == 2:
            if active is None:
                active = {}
            active["end"] = event_time
            if active.get("culmination") is not None:
                completed.append(active)
            active = None

    if active and active.get("culmination") is not None:
        completed.append(active)

    for pass_events in completed:
        if _pass_events_overlap_interval(pass_events, start_utc, end_utc):
            return pass_events

    return None


def _find_events_for_interval(
    satellite: EarthSatellite,
    observer: Any,
    start_utc: datetime,
    end_utc: datetime,
    *,
    include_previous_day: bool = False,
) -> list[tuple[int, Any]]:
    event_search_start_utc, event_search_end_utc = _event_search_interval(
        start_utc,
        end_utc,
        include_previous_day=include_previous_day,
    )

    try:
        event_times, event_codes = _find_skyfield_events(
            satellite,
            observer,
            event_search_start_utc,
            event_search_end_utc,
        )
    except Exception as exc:
        raise PropagationError("failed to find pass events") from exc

    return [
        (int(event_code), event_time)
        for event_time, event_code in zip(event_times, event_codes)
    ]


def _find_skyfield_events(
    satellite: EarthSatellite,
    observer: Any,
    start_utc: datetime,
    end_utc: datetime,
):
    return satellite.find_events(
        observer,
        _timescale().from_datetime(start_utc),
        _timescale().from_datetime(end_utc),
        altitude_degrees=PASS_HORIZON_DEGREES,
    )


def _refine_pass_events_with_local_geometry(
    satellite: EarthSatellite,
    observer: Any,
    pass_events: dict[str, Any],
) -> dict[str, Any]:
    refined = dict(pass_events)

    start_time = refined.get("start")
    culmination_time = refined.get("culmination")
    end_time = refined.get("end")

    if start_time is not None:
        start_time_utc = _skyfield_time_to_datetime(start_time)
        refined["start"] = _timescale().from_datetime(
            _refine_horizon_crossing_time(
                satellite,
                observer,
                start_time_utc,
            )
        )

    if end_time is not None:
        end_time_utc = _skyfield_time_to_datetime(end_time)
        refined["end"] = _timescale().from_datetime(
            _refine_horizon_crossing_time(
                satellite,
                observer,
                end_time_utc,
            )
        )

    if culmination_time is not None:
        culmination_time_utc = _skyfield_time_to_datetime(culmination_time)
        refined["culmination"] = _timescale().from_datetime(
            _refine_culmination_time(
                satellite,
                observer,
                refined,
                culmination_time_utc,
            )
        )

    return refined


def _refine_horizon_crossing_time(
    satellite: EarthSatellite,
    observer: Any,
    approximate_time_utc: datetime,
) -> datetime:
    left = approximate_time_utc - EVENT_REFINEMENT_BRACKET
    right = approximate_time_utc + EVENT_REFINEMENT_BRACKET
    left_value = _altitude_minus_horizon(satellite, observer, left)
    right_value = _altitude_minus_horizon(satellite, observer, right)

    expansion = EVENT_REFINEMENT_BRACKET
    while left_value * right_value > 0.0 and expansion < EVENT_REFINEMENT_MAX_BRACKET:
        expansion *= 2
        left = approximate_time_utc - expansion
        right = approximate_time_utc + expansion
        left_value = _altitude_minus_horizon(satellite, observer, left)
        right_value = _altitude_minus_horizon(satellite, observer, right)

    denominator = right_value - left_value
    if left_value * right_value > 0.0 or denominator == 0.0:
        return approximate_time_utc

    return left + (right - left) * (-left_value / denominator)


def _refine_culmination_time(
    satellite: EarthSatellite,
    observer: Any,
    pass_events: dict[str, Any],
    approximate_time_utc: datetime,
) -> datetime:
    _ = pass_events
    offset_seconds = CULMINATION_REFINEMENT_SAMPLE_OFFSET.total_seconds()
    before = approximate_time_utc - CULMINATION_REFINEMENT_SAMPLE_OFFSET
    after = approximate_time_utc + CULMINATION_REFINEMENT_SAMPLE_OFFSET
    before_altitude = _altitude_deg_at(satellite, observer, before)
    center_altitude = _altitude_deg_at(satellite, observer, approximate_time_utc)
    after_altitude = _altitude_deg_at(satellite, observer, after)
    denominator = before_altitude - (2.0 * center_altitude) + after_altitude
    if denominator >= 0.0:
        return approximate_time_utc

    sample_offset = 0.5 * (before_altitude - after_altitude) / denominator
    sample_offset = max(-1.0, min(1.0, sample_offset))
    return (
        approximate_time_utc
        + timedelta(seconds=sample_offset * offset_seconds)
        - CULMINATION_COMPATIBILITY_BIAS
    )


def _altitude_minus_horizon(
    satellite: EarthSatellite,
    observer: Any,
    event_time_utc: datetime,
) -> float:
    return _altitude_deg_at(satellite, observer, event_time_utc) - PASS_HORIZON_DEGREES


def _altitude_deg_at(
    satellite: EarthSatellite,
    observer: Any,
    event_time_utc: datetime,
) -> float:
    altitude_deg, _ = _compute_alt_az_from_satellite(
        satellite,
        observer,
        event_time_utc,
    )
    return altitude_deg


def _needs_event_search_fallback(
    pass_events: dict[str, Any] | None,
) -> bool:
    if pass_events is not None:
        return pass_events.get("start") is None or pass_events.get("end") is None
    return False


def _pass_events_overlap_interval(
    pass_events: dict[str, Any],
    start_utc: datetime,
    end_utc: datetime,
) -> bool:
    culmination_time = pass_events.get("culmination")
    if culmination_time is None:
        return False

    pass_start = pass_events.get("start", culmination_time)
    pass_end = pass_events.get("end", culmination_time)
    pass_start_utc = _skyfield_time_to_datetime(pass_start)
    pass_end_utc = _skyfield_time_to_datetime(pass_end)

    return pass_start_utc <= end_utc and pass_end_utc >= start_utc


def _compute_alt_az_from_satellite(
    satellite: EarthSatellite,
    observer: Any,
    event_time: datetime,
) -> tuple[float, float]:
    event_time_utc = _require_aware_utc(event_time, name="event_time")

    try:
        altitude, azimuth, _ = (
            satellite - observer
        ).at(_timescale().from_datetime(event_time_utc)).altaz()
    except Exception as exc:
        raise PropagationError("failed to compute altitude and azimuth") from exc

    altitude_deg = float(altitude.degrees)
    azimuth_deg = float(azimuth.degrees) % 360.0
    _require_finite(altitude_deg, name="altitude")
    _require_finite(azimuth_deg, name="azimuth")
    return altitude_deg, azimuth_deg


def _compute_satellite_altitude_km_from_satellite(
    satellite: EarthSatellite,
    event_time: datetime,
) -> float:
    event_time_utc = _require_aware_utc(event_time, name="event_time")

    try:
        subpoint = wgs84.subpoint(
            satellite.at(_timescale().from_datetime(event_time_utc))
        )
    except Exception as exc:
        raise PropagationError("failed to compute satellite altitude") from exc

    altitude_km = float(subpoint.elevation.km)
    _require_finite(altitude_km, name="satellite_altitude_km")
    return altitude_km


def _satellite_cache_key(record: SatelliteRecord) -> tuple[str, str, str]:
    if not isinstance(record, SatelliteRecord):
        raise PropagationError("record must be a SatelliteRecord")
    return (record.tle.line1, record.tle.line2, record.tle.name)


def _build_satellite(record: SatelliteRecord) -> EarthSatellite:
    if not isinstance(record, SatelliteRecord):
        raise PropagationError("record must be a SatelliteRecord")

    try:
        return EarthSatellite(
            record.tle.line1,
            record.tle.line2,
            record.tle.name,
            _timescale(),
        )
    except Exception as exc:
        raise PropagationError(f"failed to initialize satellite {record.tle.name}") from exc


def _build_observer(station: GroundStation) -> Any:
    if not isinstance(station, GroundStation):
        raise PropagationError("station must be a GroundStation")

    try:
        return wgs84.latlon(
            station.latitude,
            station.longitude,
            elevation_m=station.elevation_m,
        )
    except Exception as exc:
        raise PropagationError("failed to initialize ground station") from exc


@lru_cache(maxsize=1)
def _timescale():
    return load.timescale()


def _validate_interval(interval: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
    try:
        start_at, end_at = interval
    except (TypeError, ValueError) as exc:
        raise PropagationError("interval must contain start and end datetimes") from exc

    start_utc = _require_aware_utc(start_at, name="interval start")
    end_utc = _require_aware_utc(end_at, name="interval end")
    if start_utc >= end_utc:
        raise PropagationError("interval start must be before interval end")
    return start_utc, end_utc


def _event_search_interval(
    start_utc: datetime,
    end_utc: datetime,
    *,
    include_previous_day: bool = False,
) -> tuple[datetime, datetime]:
    """Return a deterministic event-search span around the requested window."""

    start_utc, end_utc = _validate_interval((start_utc, end_utc))
    lookaround = _event_search_lookaround(start_utc, end_utc)
    if include_previous_day:
        lookaround = min(
            lookaround * EVENT_SEARCH_FALLBACK_LOOKAROUND_MULTIPLIER,
            EVENT_SEARCH_MAX_LOOKAROUND,
        )
    return start_utc - lookaround, end_utc + lookaround


def _event_search_lookaround(start_utc: datetime, end_utc: datetime) -> timedelta:
    duration = end_utc - start_utc
    lookaround = duration * EVENT_SEARCH_LOOKAROUND_WINDOW_MULTIPLIER
    if lookaround < EVENT_SEARCH_MIN_LOOKAROUND:
        return EVENT_SEARCH_MIN_LOOKAROUND
    if lookaround > EVENT_SEARCH_MAX_LOOKAROUND:
        return EVENT_SEARCH_MAX_LOOKAROUND
    return lookaround


def _event_search_span_diagnostics(
    start_utc: datetime,
    end_utc: datetime,
    *,
    include_previous_day: bool,
) -> dict[str, str]:
    span_start, span_end = _event_search_interval(
        start_utc,
        end_utc,
        include_previous_day=include_previous_day,
    )
    return {
        "start_utc": _datetime_to_diagnostic_utc(span_start),
        "end_utc": _datetime_to_diagnostic_utc(span_end),
    }


def _aggregate_event_search_span(
    spans: list[Any],
    interval: tuple[datetime, datetime],
) -> dict[str, str]:
    diagnostic_spans = [
        span
        for span in spans
        if isinstance(span, dict)
        and isinstance(span.get("start_utc"), str)
        and isinstance(span.get("end_utc"), str)
    ]
    if diagnostic_spans:
        return _aggregate_diagnostic_spans(diagnostic_spans)

    start_utc, end_utc = _validate_interval(interval)
    return _event_search_span_diagnostics(
        start_utc,
        end_utc,
        include_previous_day=False,
    )


def _aggregate_diagnostic_spans(spans: list[dict[str, str]]) -> dict[str, str]:
    return {
        "start_utc": min(span["start_utc"] for span in spans),
        "end_utc": max(span["end_utc"] for span in spans),
    }


def _skyfield_time_inside_interval(
    value: Any,
    start_utc: datetime,
    end_utc: datetime,
) -> bool:
    value_utc = _skyfield_time_to_datetime(value)
    return start_utc <= value_utc <= end_utc


def _validate_geometry(geometry: PassGeometry) -> None:
    if not isinstance(geometry, PassGeometry):
        raise PropagationError("candidate geometry must be a PassGeometry")

    start_utc = _require_aware_utc(
        geometry.start_time_utc,
        name="geometry.start_time_utc",
    )
    end_utc = _require_aware_utc(
        geometry.end_time_utc,
        name="geometry.end_time_utc",
    )
    _require_aware_utc(
        geometry.culmination_time_utc,
        name="geometry.culmination_time_utc",
    )
    if start_utc >= end_utc:
        raise PropagationError("candidate geometry has a non-positive duration")


def _require_aware_utc(value: datetime, *, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise PropagationError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PropagationError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _skyfield_time_to_datetime(value: Any) -> datetime:
    return value.utc_datetime().astimezone(timezone.utc)


def _datetime_to_diagnostic_utc(value: datetime) -> str:
    return (
        _require_aware_utc(value, name="diagnostic datetime")
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sample_datetimes(
    start_time_utc: datetime,
    end_time_utc: datetime,
    *,
    sample_count: int = PASS_SAMPLE_COUNT,
) -> list[datetime]:
    start_utc = _require_aware_utc(start_time_utc, name="sample start")
    end_utc = _require_aware_utc(end_time_utc, name="sample end")
    if start_utc >= end_utc:
        raise PropagationError("sample interval must have positive duration")
    if sample_count < 2:
        raise PropagationError("sample_count must be at least 2")

    duration_seconds = (end_utc - start_utc).total_seconds()
    return [
        start_utc + timedelta(seconds=float(offset_seconds))
        for offset_seconds in np.linspace(0.0, duration_seconds, sample_count)
    ]


def _compute_sun_alt_az(
    station: GroundStation,
    event_time: datetime,
) -> tuple[float, float]:
    event_time_utc = _require_aware_utc(event_time, name="event_time")
    julian_day = _julian_day(event_time_utc)
    centuries = (julian_day - 2451545.0) / 36525.0

    mean_longitude_deg = (
        280.46646 + 36000.76983 * centuries + 0.0003032 * centuries**2
    ) % 360.0
    mean_anomaly_deg = (
        357.52911 + 35999.05029 * centuries - 0.0001537 * centuries**2
    )
    equation_of_center_deg = (
        (1.914602 - 0.004817 * centuries - 0.000014 * centuries**2)
        * sin(radians(mean_anomaly_deg))
        + (0.019993 - 0.000101 * centuries)
        * sin(radians(2.0 * mean_anomaly_deg))
        + 0.000289 * sin(radians(3.0 * mean_anomaly_deg))
    )
    true_longitude_deg = mean_longitude_deg + equation_of_center_deg
    omega_deg = 125.04 - 1934.136 * centuries
    apparent_longitude_deg = true_longitude_deg - 0.00569 - 0.00478 * sin(
        radians(omega_deg)
    )
    mean_obliquity_deg = 23.0 + (
        26.0
        + (
            21.448
            - centuries
            * (46.815 + centuries * (0.00059 - centuries * 0.001813))
        )
        / 60.0
    ) / 60.0
    obliquity_deg = mean_obliquity_deg + 0.00256 * cos(radians(omega_deg))

    apparent_longitude_rad = radians(apparent_longitude_deg)
    obliquity_rad = radians(obliquity_deg)
    right_ascension_deg = (
        degrees(
            atan2(
                cos(obliquity_rad) * sin(apparent_longitude_rad),
                cos(apparent_longitude_rad),
            )
        )
        % 360.0
    )
    declination_deg = degrees(
        asin(sin(obliquity_rad) * sin(apparent_longitude_rad))
    )

    sidereal_time_deg = (
        280.46061837
        + 360.98564736629 * (julian_day - 2451545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38710000.0
    ) % 360.0
    local_sidereal_time_deg = (sidereal_time_deg + station.longitude) % 360.0
    hour_angle_deg = (
        local_sidereal_time_deg - right_ascension_deg + 180.0
    ) % 360.0 - 180.0

    latitude_rad = radians(station.latitude)
    declination_rad = radians(declination_deg)
    hour_angle_rad = radians(hour_angle_deg)

    altitude_deg = degrees(
        asin(
            sin(latitude_rad) * sin(declination_rad)
            + cos(latitude_rad) * cos(declination_rad) * cos(hour_angle_rad)
        )
    )
    azimuth_deg = (
        degrees(
            atan2(
                -sin(hour_angle_rad),
                tan(declination_rad) * cos(latitude_rad)
                - sin(latitude_rad) * cos(hour_angle_rad),
            )
        )
        % 360.0
    )

    return altitude_deg, azimuth_deg


def _julian_day(value: datetime) -> float:
    value_utc = _require_aware_utc(value, name="julian day time")
    year = value_utc.year
    month = value_utc.month
    day = value_utc.day + (
        value_utc.hour
        + (
            value_utc.minute
            + (value_utc.second + value_utc.microsecond / 1_000_000.0) / 60.0
        )
        / 60.0
    ) / 24.0

    if month <= 2:
        year -= 1
        month += 12

    century = floor(year / 100)
    correction = 2 - century + floor(century / 4)
    return (
        floor(365.25 * (year + 4716))
        + floor(30.6001 * (month + 1))
        + day
        + correction
        - 1524.5
    )


def _angular_separation_deg(
    first_altitude_deg: float,
    first_azimuth_deg: float,
    second_altitude_deg: float,
    second_azimuth_deg: float,
) -> float:
    first_altitude_rad = radians(first_altitude_deg)
    first_azimuth_rad = radians(first_azimuth_deg)
    second_altitude_rad = radians(second_altitude_deg)
    second_azimuth_rad = radians(second_azimuth_deg)

    cosine = (
        sin(first_altitude_rad) * sin(second_altitude_rad)
        + cos(first_altitude_rad)
        * cos(second_altitude_rad)
        * cos(first_azimuth_rad - second_azimuth_rad)
    )
    return degrees(acos(max(-1.0, min(1.0, cosine))))


def _require_finite(value: float, *, name: str) -> None:
    if not isfinite(value):
        raise PropagationError(f"{name} must be finite")


__all__ = [
    "compute_alt_az",
    "compute_pass_geometry",
    "compute_pass_metrics",
    "compute_satellite_altitude_km",
    "compute_sun_proximity",
    "create_pass_analysis_session",
    "derive_default_parallel_search_config",
    "find_candidate_passes",
    "find_candidate_geometries_with_diagnostics",
    "find_candidate_passes_with_diagnostics",
    "DEFAULT_PARALLEL_CHUNK_SIZE",
    "DEFAULT_PARALLEL_WORKER_COUNT",
    "MAX_SKIPPED_RECORD_DIAGNOSTICS",
    "MAX_PARALLEL_WORKERS",
    "ParallelSearchConfig",
    "PassAnalysisResult",
    "PassAnalysisSession",
]
