from __future__ import annotations

import pytest


pytestmark = pytest.mark.functional


@pytest.mark.parametrize(
    ("exception_name", "expected_status", "expected_code"),
    [
        pytest.param("ValidationError", 422, "validation_error", id="validation"),
        pytest.param("TleLoadError", 503, "tle_unavailable", id="tle-load"),
        pytest.param("TleFreshnessError", 503, "tle_stale", id="tle-freshness"),
        pytest.param(
            "SearchExecutionError",
            500,
            "search_execution_error",
            id="search-execution",
        ),
    ],
)
def test_expected_core_errors_return_documented_machine_readable_payloads(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
    exception_name,
    expected_status,
    expected_code,
):
    from tlefinder.api.routers import search as search_routes
    from tlefinder.core import errors as core_errors

    client, _store_path = api_client_factory()
    exception_cls = getattr(core_errors, exception_name)

    def search_candidates(core_request):
        raise exception_cls("controlled core failure")

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert "traceback" not in response.text.lower()


def test_station_persistence_failure_after_successful_search_returns_store_error(
    api_client_factory,
    monkeypatch,
    tmp_path,
    simple_search_payload,
    core_no_result_response,
):
    from tlefinder.api.routers import search as search_routes

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("this file blocks station store creation", encoding="utf-8")
    client, _store_path = api_client_factory(
        station_store_path=blocked_parent / "stations.yaml",
    )
    monkeypatch.setattr(
        search_routes.core,
        "search_candidates",
        lambda core_request: core_no_result_response(),
    )

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "station_store_error"


def test_unexpected_errors_return_generic_internal_error_payload(
    api_client_factory,
    monkeypatch,
    simple_search_payload,
):
    from tlefinder.api.routers import search as search_routes

    client, _store_path = api_client_factory(raise_server_exceptions=False)

    def search_candidates(core_request):
        raise RuntimeError("secret backend implementation detail")

    monkeypatch.setattr(search_routes.core, "search_candidates", search_candidates)

    response = client.post("/api/v1/search/simple", json=simple_search_payload())

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret backend implementation detail" not in response.text
    assert "traceback" not in response.text.lower()
