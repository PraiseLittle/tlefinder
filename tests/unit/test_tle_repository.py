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


def _fixture_configs_by_group():
    from tlefinder.core.tle_repository import TleSourceConfig

    return {
        group: TleSourceConfig(
            url=f"https://example.invalid/{group.value}.tle",
            cache_filename="downloaded.tle",
        )
        for group in SatelliteGroup
    }


def _set_cache_mtime(path: Path, *, age: timedelta) -> None:
    timestamp = (datetime.now(timezone.utc) - age).timestamp()
    os.utime(path, (timestamp, timestamp))


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


def test_default_source_configs_cover_each_supported_satellite_group():
    from tlefinder.core.tle_repository import DEFAULT_SOURCE_CONFIGS

    assert set(DEFAULT_SOURCE_CONFIGS) == set(SatelliteGroup)


def test_default_source_configs_request_tle_format_explicitly():
    from tlefinder.core.tle_repository import DEFAULT_SOURCE_CONFIGS

    assert all("FORMAT=TLE" in config.url for config in DEFAULT_SOURCE_CONFIGS.values())


def test_default_tle_cache_age_is_one_hour():
    from tlefinder.core.tle_repository import DEFAULT_MAX_TLE_CACHE_AGE_HOURS

    assert DEFAULT_MAX_TLE_CACHE_AGE_HOURS == 1


@pytest.mark.parametrize(
    ("group", "fixture_filename"),
    [
        (SatelliteGroup.ACTIVE, "active_sample.tle"),
        (SatelliteGroup.VISUAL, "visual_sample.tle"),
        (SatelliteGroup.AMATEUR, "amateur_sample.tle"),
    ],
)
def test_load_tle_dataset_selects_requested_group_source_and_metadata(
    tmp_path,
    group,
    fixture_filename,
):
    from tlefinder.core.tle_repository import load_tle_dataset

    configs = _fixture_configs_by_group()
    expected_url = configs[group].url

    class RecordingClient:
        def __init__(self):
            self.urls: list[str] = []

        def get(self, url):
            self.urls.append(url)

            class Response:
                text = (FIXTURES_DIR / fixture_filename).read_text(encoding="utf-8")

            return Response()

    client = RecordingClient()

    records = load_tle_dataset(
        group,
        datetime(2026, 5, 13, 2, 0, tzinfo=timezone.utc),
        cache_dir=tmp_path,
        http_client=client,
        source_configs=configs,
    )

    assert client.urls == [expected_url]
    assert {record.tle.source_group for record in records} == {group}
    assert {record.metadata["source_group"] for record in records} == {group.value}


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
    _set_cache_mtime(cached_path, age=timedelta(minutes=30))

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


def test_load_tle_dataset_refreshes_cache_older_than_one_hour(
    tmp_path,
):
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(hours=1, seconds=1))

    class RefreshClient:
        def __init__(self):
            self.urls: list[str] = []

        def get(self, url):
            self.urls.append(url)

            class Response:
                text = (
                    (FIXTURES_DIR / "active_sample.tle")
                    .read_text(encoding="utf-8")
                    .replace("ISS (ZARYA)", "DOWNLOADED ISS", 1)
                )

            return Response()

    client = RefreshClient()

    records = load_tle_dataset(
        SatelliteGroup.ACTIVE,
        as_of_utc,
        cache_dir=tmp_path,
        http_client=client,
        source_configs=_fixture_config("active.tle"),
    )

    assert client.urls == ["https://example.invalid/active.tle"]
    assert len(records) == 2
    assert records[0].tle.name == "DOWNLOADED ISS"


def test_load_tle_dataset_filters_mixed_age_cache_without_network(tmp_path):
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 11, 0, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(minutes=30))

    class OfflineClient:
        def get(self, url):
            raise AssertionError("mixed fresh cache should avoid network retrieval")

    records = load_tle_dataset(
        SatelliteGroup.ACTIVE,
        as_of_utc,
        cache_dir=tmp_path,
        http_client=OfflineClient(),
        source_configs=_fixture_config("active.tle"),
    )

    assert [record.tle.name for record in records] == ["ISS (ZARYA)"]
    assert records[0].metadata["tle_dataset"] == {
        "total_record_count": 2,
        "fresh_record_count": 1,
        "stale_record_count": 1,
        "max_age_hours": 24,
    }


def test_load_tle_dataset_preserves_order_after_filtering_stale_records(tmp_path):
    from tlefinder.core.tle_repository import load_tle_dataset

    source = (FIXTURES_DIR / "active_sample.tle").read_text(encoding="utf-8")
    cached_path = tmp_path / "active.tle"
    cached_path.write_text(
        source
        + "\nFRESH THIRD\n"
        + "1 12345U 98067A   26132.95833333  .00000000  00000+0  00000+0 0  9991\n"
        + "2 12345  51.6400 123.4500 0001000  10.0000 350.0000 15.50000000000000\n",
        encoding="utf-8",
    )
    as_of_utc = datetime(2026, 5, 13, 11, 0, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(minutes=30))

    class OfflineClient:
        def get(self, url):
            raise AssertionError("mixed fresh cache should avoid network retrieval")

    records = load_tle_dataset(
        SatelliteGroup.ACTIVE,
        as_of_utc,
        cache_dir=tmp_path,
        http_client=OfflineClient(),
        source_configs=_fixture_config("active.tle"),
    )

    assert [record.tle.name for record in records] == ["ISS (ZARYA)", "FRESH THIRD"]


def test_load_tle_dataset_raises_freshness_error_for_stale_records(tmp_path):
    from tlefinder.core.errors import TleFreshnessError
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 12, 0, 1, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(minutes=30))

    class Response:
        text = (FIXTURES_DIR / "active_sample.tle").read_text(encoding="utf-8")

    class StaleDatasetClient:
        def get(self, url):
            return Response()

    with pytest.raises(TleFreshnessError, match="no fresh TLE records.*24 hours"):
        load_tle_dataset(
            SatelliteGroup.ACTIVE,
            as_of_utc,
            cache_dir=tmp_path,
            http_client=StaleDatasetClient(),
            source_configs=_fixture_config("active.tle"),
        )


def test_load_tle_dataset_raises_load_error_when_refresh_fails_even_if_cache_tles_are_fresh(
    tmp_path,
):
    from tlefinder.core.errors import TleLoadError
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 5, 0, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(hours=2))

    class FailingClient:
        def get(self, url):
            raise httpx.ConnectError("network unavailable")

    with pytest.raises(TleLoadError, match="refresh failed"):
        load_tle_dataset(
            SatelliteGroup.ACTIVE,
            as_of_utc,
            cache_dir=tmp_path,
            http_client=FailingClient(),
            source_configs=_fixture_config("active.tle"),
        )


def test_load_tle_dataset_raises_load_error_when_refresh_fails_and_cache_stale(
    tmp_path,
):
    from tlefinder.core.errors import TleLoadError
    from tlefinder.core.tle_repository import load_tle_dataset

    cached_path = tmp_path / "active.tle"
    shutil.copyfile(FIXTURES_DIR / "active_sample.tle", cached_path)
    as_of_utc = datetime(2026, 5, 13, 12, 0, 1, tzinfo=timezone.utc)
    _set_cache_mtime(cached_path, age=timedelta(hours=2))

    class FailingClient:
        def get(self, url):
            raise httpx.ConnectError("network unavailable")

    with pytest.raises(TleLoadError, match="refresh failed"):
        load_tle_dataset(
            SatelliteGroup.ACTIVE,
            as_of_utc,
            cache_dir=tmp_path,
            http_client=FailingClient(),
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


def test_download_tle_dataset_default_httpx_client_ignores_environment_proxies(
    monkeypatch,
    tmp_path,
):
    from tlefinder.core import tle_repository
    from tlefinder.core.tle_repository import download_tle_dataset

    client_kwargs: list[dict[str, object]] = []
    requested_urls: list[str] = []

    class Response:
        text = (FIXTURES_DIR / "active_sample.tle").read_text(encoding="utf-8")

    class FakeHttpxClient:
        def __init__(self, **kwargs):
            client_kwargs.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get(self, url):
            requested_urls.append(url)
            return Response()

    monkeypatch.setattr(tle_repository.httpx, "Client", FakeHttpxClient)

    downloaded_path = download_tle_dataset(
        SatelliteGroup.ACTIVE,
        cache_dir=tmp_path,
        source_configs=_fixture_config("active.tle"),
    )

    assert client_kwargs == [{"timeout": 20.0, "trust_env": False}]
    assert requested_urls == ["https://example.invalid/active.tle"]
    assert downloaded_path == tmp_path / "active.tle"


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
