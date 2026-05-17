"""Skyfield-based pass detection and metric computation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import acos, asin, atan2, cos, degrees, floor, isfinite, radians, sin, tan
from typing import Any

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


def find_candidate_passes(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> list[CandidatePass]:
    """Propagate satellite records and return detected candidate passes."""

    candidates, _ = _find_candidate_passes_with_diagnostics(records, station, interval)
    return candidates


def _find_candidate_passes_with_diagnostics(
    records: list[SatelliteRecord],
    station: GroundStation,
    interval: tuple[datetime, datetime],
) -> tuple[list[CandidatePass], list[dict[str, Any]]]:
    _validate_interval(interval)
    candidates: list[CandidatePass] = []
    skipped_diagnostics: list[dict[str, Any]] = []

    for record in records:
        geometry, diagnostics = _compute_pass_geometry_with_diagnostics(
            record,
            station,
            interval,
        )
        if geometry is None:
            skipped_diagnostics.append(_satellite_diagnostics(record, diagnostics))
            continue

        candidate = CandidatePass(
            satellite=record,
            geometry=geometry,
            metrics=PassMetrics(satellite_altitude_km=0.0),
            diagnostics=diagnostics,
        )
        candidate.metrics = compute_pass_metrics(candidate, station)
        candidates.append(candidate)

    return candidates, skipped_diagnostics


def _satellite_diagnostics(
    record: SatelliteRecord,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "satellite_name": record.tle.name,
        "catalog_number": record.tle.catalog_number,
        **diagnostics,
    }


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
    sample_times = _sample_datetimes(
        candidate.geometry.start_time_utc,
        candidate.geometry.end_time_utc,
    )
    satellite = _build_satellite(candidate.satellite)
    altitudes = [
        _compute_satellite_altitude_km_from_satellite(satellite, sample_time)
        for sample_time in sample_times
    ]

    return PassMetrics(
        satellite_altitude_km=float(np.mean(altitudes)),
        sun_proximity_deg=compute_sun_proximity(candidate, station),
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
    separations: list[float] = []

    for sample_time in _sample_datetimes(
        candidate.geometry.start_time_utc,
        candidate.geometry.end_time_utc,
    ):
        satellite_altitude_deg, satellite_azimuth_deg = _compute_alt_az_from_satellite(
            satellite,
            observer,
            sample_time,
        )
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
    satellite = _build_satellite(record)
    observer = _build_observer(station)
    events = _find_events_for_interval(
        satellite,
        observer,
        start_utc,
        end_utc,
    )
    pass_events = _select_pass_events(events, start_utc, end_utc)

    if pass_events is None or pass_events.get("start") is None:
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
        if fallback_pass_events is not None:
            events = fallback_events
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
    }

    if pass_events is None:
        diagnostics["skipped_reason"] = "no_rise_culmination_pair"
        return None, diagnostics

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
    _ = (start_altitude_deg, end_altitude_deg)

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
        event_times, event_codes = satellite.find_events(
            observer,
            _timescale().from_datetime(event_search_start_utc),
            _timescale().from_datetime(event_search_end_utc),
            altitude_degrees=PASS_HORIZON_DEGREES,
        )
    except Exception as exc:
        raise PropagationError("failed to find pass events") from exc

    return [
        (int(event_code), event_time)
        for event_time, event_code in zip(event_times, event_codes)
    ]


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

    day_start = datetime(
        start_utc.year,
        start_utc.month,
        start_utc.day,
        tzinfo=timezone.utc,
    )
    search_start = day_start
    if include_previous_day:
        search_start -= timedelta(days=1)
    search_end = day_start + timedelta(days=2)
    if end_utc > search_end:
        search_end = end_utc + timedelta(days=1)
    return search_start, search_end


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
    "find_candidate_passes",
]
