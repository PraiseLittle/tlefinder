"""Repeatable local benchmark for the core search pipeline."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import platform
from pathlib import Path
import shutil
import sys
import tempfile
from time import perf_counter
from typing import Iterator

from tlefinder.core import pass_analysis
from tlefinder.core.engine import search_candidates
from tlefinder.core.errors import TleFinderError
from tlefinder.core.models import (
    GroundStation,
    RangeConstraint,
    SatelliteGroup,
    SearchCriteria,
    SearchRequest,
    SearchWindow,
    TargetToleranceConstraint,
)
from tlefinder.core.tle_repository import (
    DEFAULT_SOURCE_CONFIGS,
    TleSourceConfig,
    parse_tle_file,
)

_DEFAULT_GROUPS = tuple(SatelliteGroup)
_DEFAULT_CASES = ("simple", "advanced")
_DEFAULT_EXECUTION_MODE = "serial_exact"
_EXECUTION_MODES = ("serial_exact", "parallel_exact", "parallel_budgeted")
_DEFAULT_PARALLEL_BACKEND = pass_analysis.PARALLEL_SEARCH_BACKEND_PROCESS_POOL
_PARALLEL_BACKENDS = (_DEFAULT_PARALLEL_BACKEND,)
_DEFAULT_START_AT = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
_DEFAULT_DURATION_MINUTES = 10.0
_DEFAULT_STATION = GroundStation(
    latitude=48.8566,
    longitude=2.3522,
    elevation_m=35.0,
)
_FIXTURE_FILENAMES = {
    SatelliteGroup.ACTIVE: "active_sample.tle",
    SatelliteGroup.VISUAL: "visual_sample.tle",
    SatelliteGroup.AMATEUR: "amateur_sample.tle",
}


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    execution_mode: str
    backend: str
    group: SatelliteGroup
    case_name: str
    status: str
    detail: str
    total_ms: float | None
    pass_analysis_ms: float | None
    scheduling_ms: float | None
    satellite_count: int | None
    processed_count: int | None
    candidate_count: int | None
    filtered_count: int | None
    returned_count: int | None
    approximate: bool | None
    cache_state: str
    tle_source_age_hours: float | None


class OfflineHttpClient:
    """Prevent benchmark runs from silently downloading missing TLE data."""

    def get(self, url: str):
        raise RuntimeError(f"local benchmark has no TLE file for {url}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    with _prepared_benchmark_source(args):
        rows = list(_run_benchmark(args))
        _print_benchmark_context(args)
        _print_rows(rows)
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the local TLE Finder core search pipeline.",
    )
    parser.add_argument(
        "--source",
        choices=("fixtures", "cache"),
        default="fixtures",
        help="Use deterministic test fixtures or a local cache directory.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Local TLE directory. Defaults to tests/fixtures for --source fixtures "
            "and tmp_tle_cache for --source cache."
        ),
    )
    parser.add_argument(
        "--groups",
        default=",".join(group.value for group in _DEFAULT_GROUPS),
        help="Comma-separated groups: active,visual,amateur.",
    )
    parser.add_argument(
        "--cases",
        default=",".join(_DEFAULT_CASES),
        help="Comma-separated cases: simple,advanced.",
    )
    parser.add_argument(
        "--execution-mode",
        choices=_EXECUTION_MODES,
        default=_DEFAULT_EXECUTION_MODE,
        help="Search execution mode: serial_exact, parallel_exact, parallel_budgeted.",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=4,
        help="Worker count for parallel execution modes.",
    )
    parser.add_argument(
        "--parallel-chunk-size",
        type=int,
        default=pass_analysis.DEFAULT_PARALLEL_CHUNK_SIZE,
        help="Chunk size for parallel execution modes.",
    )
    parser.add_argument(
        "--parallel-backend",
        choices=_PARALLEL_BACKENDS,
        default=_DEFAULT_PARALLEL_BACKEND,
        help="Backend for parallel execution modes.",
    )
    parser.add_argument(
        "--start-at",
        type=_parse_datetime,
        default=_DEFAULT_START_AT,
        help="Search start time with explicit offset, default 2026-05-12T20:00:00Z.",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=_DEFAULT_DURATION_MINUTES,
        help="Search-window duration in minutes.",
    )
    parser.add_argument(
        "--max-tle-age-hours",
        type=int,
        default=24,
        help="Freshness window passed to the core TLE repository.",
    )
    return parser.parse_args(argv)


def _run_benchmark(args: argparse.Namespace):
    groups = _parse_groups(args.groups)
    case_names = _parse_cases(args.cases)
    cache_dir = _resolve_cache_dir(args.source, args.cache_dir)
    source_configs = _source_configs(args.source)

    for group in groups:
        cache_path = cache_dir / _cache_filename(args.source, group)
        if not cache_path.exists():
            for case_name in case_names:
                yield BenchmarkRow(
                    execution_mode=args.execution_mode,
                    backend=args.parallel_backend,
                    group=group,
                    case_name=case_name,
                    status="skipped_missing_tle",
                    detail="",
                    total_ms=None,
                    pass_analysis_ms=None,
                    scheduling_ms=None,
                    satellite_count=None,
                    processed_count=None,
                    candidate_count=None,
                    filtered_count=None,
                    returned_count=None,
                    approximate=None,
                    cache_state=str(cache_path),
                    tle_source_age_hours=None,
                )
            continue

        for case_name in case_names:
            yield _run_case(
                group=group,
                case_name=case_name,
                cache_dir=cache_dir,
                source_configs=source_configs,
                start_at=args.start_at,
                duration_minutes=args.duration_minutes,
                max_tle_age_hours=args.max_tle_age_hours,
                execution_mode=args.execution_mode,
                parallel_workers=args.parallel_workers,
                parallel_chunk_size=args.parallel_chunk_size,
                parallel_backend=args.parallel_backend,
                cache_path=cache_path,
            )


def _run_case(
    *,
    group: SatelliteGroup,
    case_name: str,
    cache_dir: Path,
    source_configs: dict[SatelliteGroup, TleSourceConfig] | None,
    start_at: datetime,
    duration_minutes: float,
    max_tle_age_hours: int,
    execution_mode: str,
    parallel_workers: int,
    parallel_chunk_size: int,
    parallel_backend: str,
    cache_path: Path,
) -> BenchmarkRow:
    request = SearchRequest(
        station=_DEFAULT_STATION,
        window=SearchWindow(start_at=start_at, duration_minutes=duration_minutes),
        criteria=_criteria_for_case(case_name),
        satellite_group=group,
    )

    wall_start = perf_counter()
    try:
        response = search_candidates(
            request,
            cache_dir=cache_dir,
            http_client=OfflineHttpClient(),
            source_configs=source_configs,
            max_tle_age_hours=max_tle_age_hours,
            **_execution_kwargs(
                execution_mode,
                parallel_workers=parallel_workers,
                parallel_chunk_size=parallel_chunk_size,
                parallel_backend=parallel_backend,
            ),
        )
    except TleFinderError as exc:
        detail = str(exc)
        if exc.__cause__ is not None:
            detail = f"{detail}: {exc.__cause__}"
        return BenchmarkRow(
            execution_mode=execution_mode,
            backend=parallel_backend,
            group=group,
            case_name=case_name,
            status=f"error:{type(exc).__name__}",
            detail=detail,
            total_ms=(perf_counter() - wall_start) * 1000.0,
            pass_analysis_ms=None,
            scheduling_ms=None,
            satellite_count=None,
            processed_count=None,
            candidate_count=None,
            filtered_count=None,
            returned_count=None,
            approximate=None,
            cache_state=str(cache_path),
            tle_source_age_hours=_tle_source_age_hours(cache_path, start_at),
        )

    wall_ms = (perf_counter() - wall_start) * 1000.0
    diagnostics = response.diagnostics
    timings_ms = diagnostics.get("timings_ms", {})
    if not isinstance(timings_ms, dict):
        timings_ms = {}
    total_ms = _float_or_default(timings_ms.get("total"), wall_ms)
    pass_analysis_ms = _float_or_default(timings_ms.get("pass_analysis"), None)
    candidate_budget_diagnostics = diagnostics.get("candidate_budget", {})
    if not isinstance(candidate_budget_diagnostics, dict):
        candidate_budget_diagnostics = {}

    return BenchmarkRow(
        execution_mode=execution_mode,
        backend=parallel_backend,
        group=group,
        case_name=case_name,
        status=response.status.value,
        detail="",
        total_ms=total_ms,
        pass_analysis_ms=pass_analysis_ms,
        scheduling_ms=_scheduling_ms(total_ms, pass_analysis_ms),
        satellite_count=_int_or_none(diagnostics.get("satellite_count")),
        processed_count=_processed_satellite_count(diagnostics),
        candidate_count=_int_or_none(diagnostics.get("candidate_count")),
        filtered_count=_int_or_none(diagnostics.get("filtered_count")),
        returned_count=_int_or_none(diagnostics.get("returned_count")),
        approximate=_bool_or_none(candidate_budget_diagnostics.get("approximate")),
        cache_state=str(cache_path),
        tle_source_age_hours=_tle_source_age_hours(cache_path, start_at),
    )


def _criteria_for_case(case_name: str) -> SearchCriteria:
    if case_name == "simple":
        return SearchCriteria(
            culmination_altitude_deg=RangeConstraint(minimum=0.0, maximum=90.0),
            sun_proximity_deg=RangeConstraint(minimum=0.0, maximum=180.0),
            satellite_altitude_km=RangeConstraint(minimum=200.0, maximum=2000.0),
            score_threshold=0.0,
            result_limit=10,
        )
    if case_name == "advanced":
        return SearchCriteria(
            culmination_altitude_deg=RangeConstraint(minimum=20.0, maximum=80.0),
            start_azimuth_deg=TargetToleranceConstraint(target=270.0, tolerance=45.0),
            culmination_azimuth_deg=TargetToleranceConstraint(
                target=180.0,
                tolerance=90.0,
            ),
            sun_proximity_deg=RangeConstraint(minimum=0.0, maximum=180.0),
            satellite_altitude_km=RangeConstraint(minimum=200.0, maximum=2000.0),
            score_threshold=0.0,
            result_limit=10,
        )
    raise ValueError(f"unsupported benchmark case {case_name!r}")


def _execution_kwargs(
    execution_mode: str,
    *,
    parallel_workers: int,
    parallel_chunk_size: int,
    parallel_backend: str,
) -> dict[str, object]:
    if execution_mode == "serial_exact":
        return {}
    parallel_config = pass_analysis.ParallelSearchConfig(
        enabled=True,
        requested_worker_count=parallel_workers,
        chunk_size=parallel_chunk_size,
        backend_name=parallel_backend,
    )
    if execution_mode == "parallel_exact":
        return {"parallel_search": parallel_config}
    if execution_mode == "parallel_budgeted":
        return {
            "approximate_budgeted": True,
            "parallel_search": parallel_config,
        }
    raise ValueError(f"unsupported execution mode {execution_mode!r}")


def _print_benchmark_context(args: argparse.Namespace) -> None:
    cache_dir = _resolve_cache_dir(args.source, args.cache_dir)
    print("Benchmark context")
    print(f"cpu_count={os.cpu_count() or 1}")
    print(f"python={platform.python_version()} executable={sys.executable}")
    print(f"os={platform.platform()}")
    print(f"source={args.source} cache_dir={cache_dir}")
    print(f"execution_mode={args.execution_mode} backend={args.parallel_backend}")
    print(
        "parallel_workers="
        f"{args.parallel_workers} parallel_chunk_size={args.parallel_chunk_size}"
    )
    print(
        "window_start_utc="
        f"{args.start_at.isoformat().replace('+00:00', 'Z')} "
        f"duration_minutes={args.duration_minutes:g}"
    )
    print(
        "station="
        f"{_DEFAULT_STATION.latitude:g},"
        f"{_DEFAULT_STATION.longitude:g},"
        f"{_DEFAULT_STATION.elevation_m:g}m"
    )
    print("result_limit simple=10 advanced=10")
    print()


def _print_rows(rows: list[BenchmarkRow]) -> None:
    print(
        "mode                backend       group   case      status               "
        "total_ms  pass_ms  scheduling_ms  satellites  processed  candidates  "
        "filtered  returned  approximate  tle_age_h  cache  detail"
    )
    for row in rows:
        print(
            f"{row.execution_mode:<19} "
            f"{row.backend:<12} "
            f"{row.group.value:<7} "
            f"{row.case_name:<9} "
            f"{row.status:<20} "
            f"{_format_ms(row.total_ms):>8} "
            f"{_format_ms(row.pass_analysis_ms):>8} "
            f"{_format_ms(row.scheduling_ms):>13} "
            f"{_format_count(row.satellite_count):>10} "
            f"{_format_count(row.processed_count):>9} "
            f"{_format_count(row.candidate_count):>11} "
            f"{_format_count(row.filtered_count):>8} "
            f"{_format_count(row.returned_count):>8} "
            f"{_format_bool(row.approximate):>11} "
            f"{_format_hours(row.tle_source_age_hours):>9} "
            f"{row.cache_state} "
            f"{row.detail}"
        )


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "datetime must be ISO 8601 with an explicit UTC offset"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("datetime must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def _parse_groups(value: str) -> list[SatelliteGroup]:
    groups: list[SatelliteGroup] = []
    for raw_group in value.split(","):
        group_name = raw_group.strip()
        if not group_name:
            continue
        groups.append(SatelliteGroup(group_name))
    return groups


def _parse_cases(value: str) -> list[str]:
    case_names: list[str] = []
    for raw_case in value.split(","):
        case_name = raw_case.strip()
        if not case_name:
            continue
        if case_name not in _DEFAULT_CASES:
            raise ValueError(f"unsupported benchmark case {case_name!r}")
        case_names.append(case_name)
    return case_names


def _resolve_cache_dir(source: str, cache_dir: Path | None) -> Path:
    if cache_dir is not None:
        return cache_dir
    repo_root = Path(__file__).resolve().parents[3]
    if source == "fixtures":
        return repo_root / "tests" / "fixtures"
    return repo_root / "tmp_tle_cache"


def _source_configs(source: str) -> dict[SatelliteGroup, TleSourceConfig] | None:
    if source == "cache":
        return None
    return {
        group: TleSourceConfig(
            url=f"offline://{group.value}",
            cache_filename=filename,
        )
        for group, filename in _FIXTURE_FILENAMES.items()
    }


def _cache_filename(source: str, group: SatelliteGroup) -> str:
    if source == "fixtures":
        return _FIXTURE_FILENAMES[group]
    return DEFAULT_SOURCE_CONFIGS[group].cache_filename


@contextmanager
def _prepared_benchmark_source(args: argparse.Namespace) -> Iterator[None]:
    if args.source != "fixtures":
        yield
        return

    original_cache_dir = args.cache_dir
    if args.cache_dir is not None:
        _copy_fixture_tles(args.cache_dir)
        yield
        return

    with tempfile.TemporaryDirectory(prefix="tlefinder-benchmark-") as temp_dir:
        args.cache_dir = Path(temp_dir)
        _copy_fixture_tles(args.cache_dir)
        try:
            yield
        finally:
            args.cache_dir = original_cache_dir


def _copy_fixture_tles(target_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    fixture_dir = repo_root / "tests" / "fixtures"
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in _FIXTURE_FILENAMES.values():
        target_path = target_dir / filename
        shutil.copyfile(fixture_dir / filename, target_path)
        target_path.touch()


def _float_or_default(value: object, default: float | None) -> float | None:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _scheduling_ms(
    total_ms: float | None,
    pass_analysis_ms: float | None,
) -> float | None:
    if total_ms is None or pass_analysis_ms is None:
        return None
    return max(0.0, total_ms - pass_analysis_ms)


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _bool_or_none(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _processed_satellite_count(diagnostics: dict[str, object]) -> int | None:
    candidate_budget = diagnostics.get("candidate_budget")
    if isinstance(candidate_budget, dict):
        processed_count = _int_or_none(candidate_budget.get("processed_satellite_count"))
        if processed_count is not None:
            return processed_count
    pass_analysis_diagnostics = diagnostics.get("pass_analysis")
    if isinstance(pass_analysis_diagnostics, dict):
        processed_count = _int_or_none(
            pass_analysis_diagnostics.get("processed_satellite_count")
        )
        if processed_count is not None:
            return processed_count
        inspected_count = _int_or_none(
            pass_analysis_diagnostics.get("satellite_records_inspected")
        )
        if inspected_count is not None:
            return inspected_count
    return _int_or_none(diagnostics.get("satellite_count"))


def _tle_source_age_hours(cache_path: Path, start_at: datetime) -> float | None:
    if not cache_path.exists():
        return None
    try:
        records = parse_tle_file(cache_path)
    except Exception:
        return None
    if not records:
        return None
    newest_epoch = max(record.epoch_utc for record in records)
    age_hours = (
        start_at.astimezone(timezone.utc) - newest_epoch.astimezone(timezone.utc)
    ).total_seconds() / 3600.0
    return round(age_hours, 3)


def _format_ms(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_hours(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_count(value: int | None) -> str:
    if value is None:
        return "-"
    return str(value)


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "-"
    return "yes" if value else "no"


if __name__ == "__main__":
    raise SystemExit(main())
