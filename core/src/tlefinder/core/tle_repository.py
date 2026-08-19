"""TLE acquisition, parsing, cache policy, and freshness enforcement."""

from __future__ import annotations

from calendar import isleap
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Protocol

import httpx

from tlefinder.core.errors import TleFreshnessError, TleLoadError
from tlefinder.core.models import SatelliteGroup, SatelliteRecord, TleRecord

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "tlefinder" / "tle"
DEFAULT_MAX_TLE_CACHE_AGE_HOURS = 2
DEFAULT_MAX_TLE_AGE_HOURS = 24
_CELESTRAK_NOT_UPDATED_MARKERS = (
    "GP data has not updated since your last successful",
    "Data is updated once every 2 hours",
)


@dataclass(frozen=True, slots=True)
class TleSourceConfig:
    """Download and cache settings for one TLE source group."""

    url: str
    cache_filename: str


class HttpClient(Protocol):
    """Minimal HTTP client interface used for repository tests."""

    def get(self, url: str): ...


class _TleSourceNotUpdatedError(Exception):
    """Raised when CelesTrak reports that cached GP data is still current."""


DEFAULT_SOURCE_CONFIGS: dict[SatelliteGroup, TleSourceConfig] = {
    SatelliteGroup.ACTIVE: TleSourceConfig(
        url="https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE",
        cache_filename="active.tle",
    ),
    SatelliteGroup.VISUAL: TleSourceConfig(
        url="https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=TLE",
        cache_filename="visual.tle",
    ),
    SatelliteGroup.AMATEUR: TleSourceConfig(
        url="https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=TLE",
        cache_filename="amateur.tle",
    ),
}


def load_tle_dataset(
    group: SatelliteGroup,
    as_of_utc: datetime,
    *,
    cache_dir: Path | str | None = None,
    http_client: HttpClient | None = None,
    source_configs: dict[SatelliteGroup, TleSourceConfig] | None = None,
    max_age_hours: int = DEFAULT_MAX_TLE_AGE_HOURS,
) -> list[SatelliteRecord]:
    """Load a cached or freshly downloaded TLE dataset for ``group``."""

    config = _source_config_for(group, source_configs)
    cache_path = _cache_path(cache_dir, config)

    if cache_path.exists() and _is_cache_file_fresh(cache_path):
        cached_records = _parse_tle_file(cache_path, source_group=group)
        fresh_records, freshness_metadata = _filter_fresh_records_with_metadata(
            cached_records,
            as_of_utc,
            max_age_hours=max_age_hours,
        )
        if fresh_records:
            return build_satellite_records(
                fresh_records,
                dataset_metadata=freshness_metadata,
            )

    try:
        source_path = download_tle_dataset(
            group,
            cache_dir=cache_dir,
            http_client=http_client,
            source_configs=source_configs,
        )
    except TleLoadError as exc:
        if not cache_path.exists():
            raise

        raise TleLoadError(
            f"cached TLE dataset for {group.value} is older than "
            f"{DEFAULT_MAX_TLE_CACHE_AGE_HOURS:g} hours and refresh failed"
        ) from exc

    tle_records = _parse_tle_file(source_path, source_group=group)
    fresh_records, freshness_metadata = _filter_fresh_records_with_metadata(
        tle_records,
        as_of_utc,
        max_age_hours=max_age_hours,
    )
    if not fresh_records:
        raise _no_fresh_tle_records_error(
            group,
            max_age_hours=max_age_hours,
            freshness_metadata=freshness_metadata,
        )

    return build_satellite_records(
        fresh_records,
        dataset_metadata=freshness_metadata,
    )


def download_tle_dataset(
    group: SatelliteGroup,
    *,
    cache_dir: Path | str | None = None,
    http_client: HttpClient | None = None,
    source_configs: dict[SatelliteGroup, TleSourceConfig] | None = None,
) -> Path:
    """Download the configured TLE source for ``group`` into the local cache."""

    config = _source_config_for(group, source_configs)
    cache_path = _cache_path(cache_dir, config)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        text = _download_text(config.url, http_client=http_client)
    except _TleSourceNotUpdatedError as exc:
        if cache_path.exists():
            _mark_cache_checked(cache_path)
            return cache_path

        raise TleLoadError(
            f"TLE source for {group.value} reports no newer data, "
            "but no local cache exists"
        ) from exc
    except Exception as exc:
        raise TleLoadError(
            f"failed to download TLE dataset for {group.value}"
        ) from exc

    if not text.strip():
        raise TleLoadError(f"downloaded TLE dataset for {group.value} is empty")

    try:
        cache_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise TleLoadError(f"failed to cache TLE dataset at {cache_path}") from exc

    return cache_path


def parse_tle_file(path: Path | str) -> list[TleRecord]:
    """Parse a named TLE file into typed records."""

    source_path = Path(path)
    source_group = _infer_source_group(source_path)
    return _parse_tle_file(source_path, source_group=source_group)


def build_satellite_records(
    tle_records: list[TleRecord],
    *,
    dataset_metadata: dict[str, int | float] | None = None,
) -> list[SatelliteRecord]:
    """Create satellite-level records from raw TLE records."""

    satellite_records: list[SatelliteRecord] = []
    for record in tle_records:
        metadata = {
            "catalog_number": record.catalog_number,
            "source_group": record.source_group.value,
        }
        if dataset_metadata is not None:
            metadata["tle_dataset"] = dict(dataset_metadata)
        satellite_records.append(
            SatelliteRecord(
                tle=record,
                aliases=(record.name,),
                metadata=metadata,
            )
        )
    return satellite_records


def is_tle_fresh(
    records: list[TleRecord],
    as_of_utc: datetime,
    max_age_hours: int = DEFAULT_MAX_TLE_AGE_HOURS,
) -> bool:
    """Return whether all TLE records are no older than ``max_age_hours``."""

    if not records:
        return False

    reference_time = _require_aware_utc(as_of_utc, name="as_of_utc")
    max_age = timedelta(hours=max_age_hours)

    for record in records:
        epoch_utc = _require_aware_utc(record.epoch_utc, name="record.epoch_utc")
        if reference_time - epoch_utc > max_age:
            return False

    return True


def filter_fresh_tle_records(
    records: list[TleRecord],
    as_of_utc: datetime,
    max_age_hours: int = DEFAULT_MAX_TLE_AGE_HOURS,
) -> list[TleRecord]:
    """Return fresh TLE records in their original source order."""

    fresh_records, _ = _filter_fresh_records_with_metadata(
        records,
        as_of_utc,
        max_age_hours=max_age_hours,
    )
    return fresh_records


def _filter_fresh_records_with_metadata(
    records: list[TleRecord],
    as_of_utc: datetime,
    *,
    max_age_hours: int,
) -> tuple[list[TleRecord], dict[str, int | float]]:
    reference_time = _require_aware_utc(as_of_utc, name="as_of_utc")
    max_age = timedelta(hours=max_age_hours)

    fresh_records: list[TleRecord] = []
    for record in records:
        epoch_utc = _require_aware_utc(record.epoch_utc, name="record.epoch_utc")
        if reference_time - epoch_utc <= max_age:
            fresh_records.append(record)

    total_count = len(records)
    fresh_count = len(fresh_records)
    return (
        fresh_records,
        {
            "total_record_count": total_count,
            "fresh_record_count": fresh_count,
            "stale_record_count": total_count - fresh_count,
            "max_age_hours": max_age_hours,
        },
    )


def _download_text(url: str, *, http_client: HttpClient | None) -> str:
    if http_client is not None:
        response = http_client.get(url)
    else:
        with httpx.Client(timeout=20.0, trust_env=False) as client:
            response = client.get(url)

    text = getattr(response, "text", "")
    if _is_celestrak_not_updated_response(response, text):
        raise _TleSourceNotUpdatedError(text.strip())

    if hasattr(response, "raise_for_status"):
        response.raise_for_status()
    return text


def _is_celestrak_not_updated_response(response, text: str) -> bool:
    return (
        getattr(response, "status_code", None) == 403
        and all(marker in text for marker in _CELESTRAK_NOT_UPDATED_MARKERS)
    )


def _mark_cache_checked(path: Path) -> None:
    try:
        path.touch()
    except OSError:
        return


def _parse_tle_file(path: Path, *, source_group: SatelliteGroup) -> list[TleRecord]:
    try:
        lines = [
            line.rstrip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError as exc:
        raise TleLoadError(f"failed to read TLE file {path}") from exc

    if len(lines) % 3 != 0:
        raise TleLoadError(f"malformed TLE file {path}: expected name/line1/line2 records")

    records: list[TleRecord] = []
    for index in range(0, len(lines), 3):
        name = lines[index].strip()
        line1 = lines[index + 1].strip()
        line2 = lines[index + 2].strip()

        try:
            records.append(
                TleRecord(
                    name=_validate_name(name),
                    line1=_validate_line(line1, expected_prefix="1 "),
                    line2=_validate_line(line2, expected_prefix="2 "),
                    catalog_number=_catalog_number_from_lines(line1, line2),
                    epoch_utc=_epoch_from_line1(line1),
                    source_group=source_group,
                    source_path=path,
                )
            )
        except ValueError as exc:
            raise TleLoadError(f"malformed TLE file {path}: {exc}") from exc

    if not records:
        raise TleLoadError(f"malformed TLE file {path}: no records found")

    return records


def _validate_name(name: str) -> str:
    if not name:
        raise ValueError("satellite name is missing")
    return name


def _validate_line(line: str, *, expected_prefix: str) -> str:
    if not line.startswith(expected_prefix):
        raise ValueError(f"expected TLE line starting with {expected_prefix!r}")
    if len(line) < 32:
        raise ValueError("TLE line is too short")
    return line


def _catalog_number_from_lines(line1: str, line2: str) -> int:
    catalog_1 = line1[2:7]
    catalog_2 = line2[2:7]
    if not catalog_1.isdigit() or not catalog_2.isdigit():
        raise ValueError("catalog number is invalid")
    if catalog_1 != catalog_2:
        raise ValueError("catalog numbers do not match")
    return int(catalog_1)


def _epoch_from_line1(line1: str) -> datetime:
    epoch_field = line1[18:32].strip()
    if len(epoch_field) < 5:
        raise ValueError("epoch field is invalid")

    try:
        year_suffix = int(epoch_field[:2])
        day_of_year = Decimal(epoch_field[2:])
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("epoch field is invalid") from exc

    year = 1900 + year_suffix if year_suffix >= 57 else 2000 + year_suffix
    max_day = 366 if isleap(year) else 365
    if day_of_year < Decimal(1) or day_of_year >= Decimal(max_day + 1):
        raise ValueError("epoch day is outside the year")

    elapsed_days = day_of_year - Decimal(1)
    microseconds_per_day = Decimal(86_400_000_000)
    elapsed_microseconds = int(
        (elapsed_days * microseconds_per_day).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )

    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=elapsed_microseconds
    )


def _infer_source_group(path: Path) -> SatelliteGroup:
    filename = path.name.lower()
    for group in SatelliteGroup:
        if group.value in filename:
            return group
    raise TleLoadError(f"cannot infer satellite group from TLE filename {path.name!r}")


def _source_config_for(
    group: SatelliteGroup,
    source_configs: dict[SatelliteGroup, TleSourceConfig] | None,
) -> TleSourceConfig:
    if not isinstance(group, SatelliteGroup):
        raise TleLoadError("satellite group must be a SatelliteGroup")

    configs = DEFAULT_SOURCE_CONFIGS if source_configs is None else source_configs
    try:
        return configs[group]
    except KeyError as exc:
        raise TleLoadError(f"no TLE source configured for {group.value}") from exc


def _cache_path(
    cache_dir: Path | str | None,
    config: TleSourceConfig,
) -> Path:
    directory = DEFAULT_CACHE_DIR if cache_dir is None else Path(cache_dir)
    return directory / config.cache_filename


def _is_cache_file_fresh(path: Path) -> bool:
    try:
        modified_at_utc = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return False

    max_age = timedelta(hours=DEFAULT_MAX_TLE_CACHE_AGE_HOURS)
    return datetime.now(timezone.utc) - modified_at_utc <= max_age


def _no_fresh_tle_records_error(
    group: SatelliteGroup,
    *,
    max_age_hours: int,
    freshness_metadata: dict[str, int | float],
) -> TleFreshnessError:
    return TleFreshnessError(
        f"no fresh TLE records remain for {group.value} within "
        f"{max_age_hours:g} hours "
        f"({freshness_metadata['stale_record_count']} stale of "
        f"{freshness_metadata['total_record_count']} total)"
    )


def _require_aware_utc(value: datetime, *, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "DEFAULT_CACHE_DIR",
    "DEFAULT_MAX_TLE_CACHE_AGE_HOURS",
    "DEFAULT_MAX_TLE_AGE_HOURS",
    "DEFAULT_SOURCE_CONFIGS",
    "TleSourceConfig",
    "build_satellite_records",
    "download_tle_dataset",
    "filter_fresh_tle_records",
    "is_tle_fresh",
    "load_tle_dataset",
    "parse_tle_file",
]
