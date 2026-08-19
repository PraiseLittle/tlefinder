from __future__ import annotations

import pytest


pytestmark = pytest.mark.functional


def test_openapi_json_is_reachable_from_created_app(api_client_factory):
    client, _store_path = api_client_factory()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert openapi["info"]["title"] == "TLE Finder API"
    assert openapi["info"]["version"] == "1.0.0"


def test_openapi_lists_all_station_and_search_routes(api_client_factory):
    client, _store_path = api_client_factory()

    paths = client.get("/openapi.json").json()["paths"]

    assert "get" in paths["/api/v1/stations"]
    assert "put" in paths["/api/v1/stations"]
    assert "post" in paths["/api/v1/search/simple"]
    assert "post" in paths["/api/v1/search/advanced"]


def test_openapi_exposes_public_schema_components(api_client_factory):
    client, _store_path = api_client_factory()

    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert {
        "SimpleSearchRequest",
        "AdvancedSearchRequest",
        "AdvancedSearchCriteria",
        "StationListRequest",
        "StationListResponse",
        "SearchResponse",
        "SearchResultResponse",
        "ErrorResponse",
        "ApiError",
        "FieldError",
    }.issubset(schemas)


@pytest.mark.parametrize(
    ("path", "method", "expected_error_statuses"),
    [
        pytest.param("/api/v1/stations", "get", {"422", "500"}, id="stations-get"),
        pytest.param("/api/v1/stations", "put", {"422", "500"}, id="stations-put"),
        pytest.param(
            "/api/v1/search/simple",
            "post",
            {"422", "500", "503"},
            id="simple-search",
        ),
        pytest.param(
            "/api/v1/search/advanced",
            "post",
            {"422", "500", "503"},
            id="advanced-search",
        ),
    ],
)
def test_openapi_declares_machine_readable_error_responses(
    api_client_factory,
    path,
    method,
    expected_error_statuses,
):
    client, _store_path = api_client_factory()

    operation = client.get("/openapi.json").json()["paths"][path][method]

    assert expected_error_statuses.issubset(operation["responses"])
    for status_code in expected_error_statuses:
        response_schema = operation["responses"][status_code]["content"][
            "application/json"
        ]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/ErrorResponse"}


def test_openapi_documents_rejection_of_unsupported_fields(api_client_factory):
    client, _store_path = api_client_factory()

    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert schemas["SimpleSearchRequest"]["additionalProperties"] is False
    assert "criteria" not in schemas["SimpleSearchRequest"]["properties"]
    assert "tle_age_limit" in schemas["SimpleSearchRequest"]["properties"]
    assert schemas["AdvancedSearchRequest"]["additionalProperties"] is False
    assert "tle_age_limit" in schemas["AdvancedSearchRequest"]["properties"]
    assert schemas["AdvancedSearchCriteria"]["additionalProperties"] is False
    assert "object_type" not in schemas["AdvancedSearchCriteria"]["properties"]
