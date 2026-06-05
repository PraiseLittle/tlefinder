from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit


def test_benchmark_cli_parses_parallel_execution_options():
    from tlefinder.benchmarks import core_search

    args = core_search._parse_args(
        [
            "--execution-mode",
            "parallel_budgeted",
            "--parallel-workers",
            "6",
            "--parallel-chunk-size",
            "64",
            "--parallel-backend",
            "process_pool",
        ]
    )

    assert args.execution_mode == "parallel_budgeted"
    assert args.parallel_workers == 6
    assert args.parallel_chunk_size == 64
    assert args.parallel_backend == "process_pool"


def test_benchmark_execution_kwargs_select_exact_and_budgeted_modes():
    from tlefinder.benchmarks import core_search
    from tlefinder.core import pass_analysis

    assert (
        core_search._execution_kwargs(
            "serial_exact",
            parallel_workers=4,
            parallel_chunk_size=32,
            parallel_backend="process_pool",
        )
        == {}
    )

    parallel_exact = core_search._execution_kwargs(
        "parallel_exact",
        parallel_workers=3,
        parallel_chunk_size=16,
        parallel_backend="process_pool",
    )
    assert set(parallel_exact) == {"parallel_search"}
    exact_config = parallel_exact["parallel_search"]
    assert isinstance(exact_config, pass_analysis.ParallelSearchConfig)
    assert exact_config.enabled is True
    assert exact_config.requested_worker_count == 3
    assert exact_config.chunk_size == 16
    assert exact_config.backend_name == "process_pool"

    parallel_budgeted = core_search._execution_kwargs(
        "parallel_budgeted",
        parallel_workers=2,
        parallel_chunk_size=8,
        parallel_backend="process_pool",
    )
    assert parallel_budgeted["approximate_budgeted"] is True
    budgeted_config = parallel_budgeted["parallel_search"]
    assert isinstance(budgeted_config, pass_analysis.ParallelSearchConfig)
    assert budgeted_config.requested_worker_count == 2
    assert budgeted_config.chunk_size == 8


def test_benchmark_row_extracts_comparison_diagnostics(monkeypatch, tmp_path):
    from tlefinder.benchmarks import core_search
    from tlefinder.core.models import SatelliteGroup, SearchResponse, SearchStatus

    def search_candidates(core_request, **kwargs):
        assert kwargs["parallel_search"].requested_worker_count == 4
        assert kwargs["parallel_search"].chunk_size == 32
        assert kwargs["approximate_budgeted"] is True
        return SearchResponse(
            results=[],
            status=SearchStatus.NO_RESULT,
            diagnostics={
                "timings_ms": {
                    "total": 25.0,
                    "pass_analysis": 18.5,
                },
                "satellite_count": 1000,
                "candidate_count": 42,
                "returned_count": 10,
                "candidate_budget": {
                    "processed_satellite_count": 640,
                    "approximate": True,
                },
            },
        )

    cache_path = tmp_path / "active.tle"
    cache_path.write_text(
        "ISS (ZARYA)\n"
        "1 25544U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991\n"
        "2 25544  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(core_search, "search_candidates", search_candidates)

    row = core_search._run_case(
        group=SatelliteGroup.ACTIVE,
        case_name="simple",
        cache_dir=tmp_path,
        source_configs=None,
        start_at=datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc),
        duration_minutes=10.0,
        max_tle_age_hours=24,
        execution_mode="parallel_budgeted",
        parallel_workers=4,
        parallel_chunk_size=32,
        parallel_backend="process_pool",
        cache_path=cache_path,
    )

    assert row.total_ms == 25.0
    assert row.pass_analysis_ms == 18.5
    assert row.scheduling_ms == pytest.approx(6.5)
    assert row.satellite_count == 1000
    assert row.processed_count == 640
    assert row.candidate_count == 42
    assert row.returned_count == 10
    assert row.approximate is True
    assert row.tle_source_age_hours == pytest.approx(8.0)


def test_benchmark_output_includes_parallel_comparison_columns(capsys):
    from tlefinder.benchmarks import core_search
    from tlefinder.core.models import SatelliteGroup

    row = core_search.BenchmarkRow(
        execution_mode="parallel_exact",
        backend="process_pool",
        group=SatelliteGroup.ACTIVE,
        case_name="simple",
        status="results",
        detail="",
        total_ms=30.0,
        pass_analysis_ms=20.0,
        scheduling_ms=10.0,
        satellite_count=1000,
        processed_count=1000,
        candidate_count=42,
        filtered_count=12,
        returned_count=10,
        approximate=False,
        cache_state="warm",
        tle_source_age_hours=1.5,
    )

    core_search._print_rows([row])

    output = capsys.readouterr().out
    assert "mode" in output
    assert "backend" in output
    assert "scheduling_ms" in output
    assert "processed" in output
    assert "approximate" in output
    assert "tle_age_h" in output
    assert "parallel_exact" in output
    assert "process_pool" in output


def test_default_parallel_settings_are_derived_without_network_access():
    from tlefinder.core import pass_analysis

    config = pass_analysis.derive_default_parallel_search_config(
        enabled=True,
        cpu_count=128,
    )

    assert config.enabled is True
    assert config.requested_worker_count == pass_analysis.DEFAULT_PARALLEL_WORKER_COUNT
    assert config.requested_worker_count <= pass_analysis.MAX_PARALLEL_WORKERS
    assert config.chunk_size == pass_analysis.DEFAULT_PARALLEL_CHUNK_SIZE
    assert config.backend_name == pass_analysis.PARALLEL_SEARCH_BACKEND_PROCESS_POOL


def test_unsafe_parallel_worker_counts_are_rejected_or_clamped():
    from tlefinder.core import pass_analysis
    from tlefinder.core.errors import PropagationError

    with pytest.raises(PropagationError, match="requested_worker_count must be <= "):
        pass_analysis.ParallelSearchConfig(
            enabled=True,
            requested_worker_count=pass_analysis.MAX_PARALLEL_WORKERS + 1,
        )

    config = pass_analysis.derive_default_parallel_search_config(
        enabled=True,
        cpu_count=pass_analysis.MAX_PARALLEL_WORKERS + 100,
    )

    assert config.requested_worker_count <= pass_analysis.MAX_PARALLEL_WORKERS
