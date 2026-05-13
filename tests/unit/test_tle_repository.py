from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from tlefinder.core.models import SatelliteGroup


pytestmark = pytest.mark.unit

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


def _load_fixture_metadata() -> dict[str, list[dict[str, object]]]:
    return json.loads((FIXTURES_DIR / "tle_metadata.json").read_text(encoding="utf-8"))


def _fixture_config(filename: str):
    from tlefinder.core.tle_repository import TleSourceConfig

    return {
        SatelliteGroup.ACTIVE: TleSourceConfig(
            url="https://example.invalid/active.tle",
            cache_filename=filename,
        )
    }


@pytest.mark.parametrize(
    ("filename", "group"),
    [
        ("active_sample.tle", SatelliteGroup.ACTIVE),
        ("visual_sample.tle", SatelliteGroup.VISUAL),
        ("amateur_sample.tle", SatelliteGroup.AMATEUR),
    ],
)
def test_parse_tle_file_returns_typed_records(filename, group):
    from tlefinder.core.tle_repository import parse_tle_file

    records = parse_tle_file(FIXTURES_DIR / filename)
    expected_records = _load_fixture_metadata()[filename]

    assert len(records) == len(expected_records)
    for record, expected in zip(records, expected_records, strict=True):
        assert record.name == expected["name"]
        assert record.catalog_number == expected["catalog_number"]
        assert record.epoch_utc == datetime.fromisoformat(expected["epoch_utc"])
        assert record.source_group is group
        assert record.source_path == FIXTURES_DIR / filename
        assert record.line1.startswith("1 ")
        assert record.line2.startswith("2 ")


def test_build_satellite_records_preserves_tle_identity():
    from tlefinder.core.tle_repository import (
        build_satellite_records,
        parse_tle_file,
    )

    tle_records = parse_tle_file(FIXTURES_DIR / "active_sample.tle")
    satellite_records = build_satellite_records(tle_records)

    assert [record.tle for record in satellite_records] == tle_records
    assert satellite_records[0].aliases == ("ISS (ZARYA)",)
    assert satellite_records[0].metadata == {
        "catalog_number": 25544,
        "source_group": "active",
    }


def test_is_tle_fresh_rejects_records_older_than_24_hours():
    from tlefinder.core.models import TleRecord
    from tlefinder.core.tle_repository import is_tle_fresh, parse_tle_file

    records = parse_tle_file(FIXTURES_DIR / "active_sample.tle")
    as_of_utc = datetime(2026, 5, 13, 6, 0, 1, tzinfo=timezone.utc)
    stale_record = TleRecord(
        name=records[0].name,
        line1=records[0].line1,
        line2=records[0].line2,
        catalog_number=records[0].catalog_number,
        epoch_utc=as_of_utc - timedelta(hours=24, seconds=1),
        source_group=records[0].source_group,
        source_path=records[0].source_path,
    )

    assert not is_tle_fresh([stale_record], as_of_utc)


def test_load_tle_dataset_reuses_fresh_cache_without_network(tmp_path):
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc)
    fresh_cache_timestamp = (as_of_utc - timedelta(hours=1)).timestamp()
    os.utime(cached_path, (fresh_cache_timestamp, fresh_cache_timestamp))

    class OfflineClient:
        def get(self, url):
            raise AssertionError("fresh cache should avoid network retrieval")

    records = load_tle_dataset(
        SatelliteGroup.ACTIVE,
        as_of_utc,
        cache_dir=tmp_path,
        http_client=OfflineClient(),
        source_configs=_fixture_config("active.tle"),
    )

    assert len(records) == 2
    assert records[0].tle.name == "ISS (ZARYA)"


def test_load_tle_dataset_raises_freshness_error_for_stale_records(tmp_path):
    from tlefinder.core.errors import TleFreshnessError
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 12, 0, 1, tzinfo=timezone.utc)
    fresh_cache_timestamp = (as_of_utc - timedelta(minutes=5)).timestamp()
    os.utime(cached_path, (fresh_cache_timestamp, fresh_cache_timestamp))

    with pytest.raises(TleFreshnessError, match="24 hours"):
        load_tle_dataset(
            SatelliteGroup.ACTIVE,
            as_of_utc,
            cache_dir=tmp_path,
            source_configs=_fixture_config("active.tle"),
        )


def test_download_tle_dataset_wraps_retrieval_failure(tmp_path):
    from tlefinder.core.errors import TleLoadError
    from tlefinder.core.tle_repository import download_tle_dataset

    class FailingClient:
        def get(self, url):
            raise httpx.ConnectError("network unavailable")

    with pytest.raises(TleLoadError, match="download"):
        download_tle_dataset(
            SatelliteGroup.ACTIVE,
            cache_dir=tmp_path,
            http_client=FailingClient(),
            source_configs=_fixture_config("active.tle"),
        )


def test_parse_tle_file_wraps_malformed_file(tmp_path):
    from tlefinder.core.errors import TleLoadError
    from tlefinder.core.tle_repository import parse_tle_file

    malformed_path = tmp_path / "active.tle"
    malformed_path.write_text(
        "BROKEN SAT\n"
        "1 12345U 98067A   26132.50000000  .00000000  00000+0  00000+0 0  9991\n",
        encoding="utf-8",
    )

    with pytest.raises(TleLoadError, match="malformed"):
        parse_tle_file(malformed_path)
