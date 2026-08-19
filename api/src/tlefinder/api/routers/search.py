"""Search execution routes for the TLE Finder API."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request

from tlefinder.api import adapters, station_store
from tlefinder.api.schemas import (
    AdvancedSearchRequest,
    ErrorResponse,
    SearchResponse,
    SearchStation,
    SimpleSearchRequest,
)
import tlefinder.core as core
import tlefinder.core.pass_analysis as pass_analysis

router = APIRouter(tags=["search"])

_SIMPLE_SEARCH_EXAMPLE = {
    "station": {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    },
    "window": {
        "start_at": "2026-05-12T20:00:00Z",
        "duration_minutes": 10,
    },
    "tle_age_limit": "24h",
}

_ADVANCED_SEARCH_EXAMPLE = {
    "station": {
        "name": "Paris Observatory",
        "latitude": 48.8367,
        "longitude": 2.3365,
        "elevation_m": 67.0,
    },
    "window": {
        "start_at": "2026-05-12T20:00:00+00:00",
        "duration_minutes": 10,
    },
    "satellite_group": "active",
    "tle_age_limit": "1w",
    "criteria": {
        "culmination_altitude_deg": {"minimum": 20, "maximum": 80},
        "start_azimuth_deg": {"target": 270, "tolerance": 20},
        "sun_proximity_deg": {"minimum": 30, "maximum": 180},
        "satellite_altitude_km": {"minimum": 400, "maximum": 1200},
        "result_limit": 5,
        "score_threshold": 60,
    },
}

_NO_RESULT_EXAMPLE = {
    "status": "no_result",
    "results": [],
    "diagnostics": {
        "satellite_count": 1200,
        "candidate_count": 0,
        "returned_count": 0,
    },
}

_ERROR_EXAMPLES = {
    "validation_error": {
        "summary": "Validation error",
        "value": {
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": {},
                "field_errors": [
                    {
                        "field": "window.duration_minutes",
                        "message": (
                            "duration_minutes must be greater than 0 and "
                            "no greater than 30"
                        ),
                    }
                ],
            }
        },
    },
    "station_store_error": {
        "summary": "Station persistence error",
        "value": {
            "error": {
                "code": "station_store_error",
                "message": "Station store operation failed.",
                "details": {},
                "field_errors": [],
            }
        },
    },
    "tle_unavailable": {
        "summary": "TLE unavailable",
        "value": {
            "error": {
                "code": "tle_unavailable",
                "message": "Required TLE data could not be loaded.",
                "details": {},
                "field_errors": [],
            }
        },
    },
}

_SEARCH_ERROR_RESPONSES = {
    422: {
        "model": ErrorResponse,
        "description": "Request or core validation failed.",
        "content": {
            "application/json": {
                "examples": {"validation_error": _ERROR_EXAMPLES["validation_error"]}
            }
        },
    },
    500: {
        "model": ErrorResponse,
        "description": "Search execution or station persistence failed.",
        "content": {
            "application/json": {
                "examples": {
                    "station_store_error": _ERROR_EXAMPLES["station_store_error"]
                }
            }
        },
    },
    503: {
        "model": ErrorResponse,
        "description": "Required TLE data is unavailable or stale.",
        "content": {
            "application/json": {
                "examples": {"tle_unavailable": _ERROR_EXAMPLES["tle_unavailable"]}
            }
        },
    },
}


@router.post(
    "/search/simple",
    response_model=SearchResponse,
    responses=_SEARCH_ERROR_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "simple_search": {
                            "summary": "Simple search",
                            "value": _SIMPLE_SEARCH_EXAMPLE,
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "examples": {
                            "no_result": {
                                "summary": "No result",
                                "value": _NO_RESULT_EXAMPLE,
                            }
                        }
                    }
                }
            }
        },
    },
)
def simple_search(
    body: SimpleSearchRequest,
    request: Request,
) -> SearchResponse:
    """Execute a simple satellite search."""
    return _execute_search(
        body,
        request,
        adapters.simple_search_to_core_request,
        approximate_budgeted=True,
    )


@router.post(
    "/search/advanced",
    response_model=SearchResponse,
    responses=_SEARCH_ERROR_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "advanced_search": {
                            "summary": "Advanced search",
                            "value": _ADVANCED_SEARCH_EXAMPLE,
                        }
                    }
                }
            }
        },
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "examples": {
                            "no_result": {
                                "summary": "No result",
                                "value": _NO_RESULT_EXAMPLE,
                            }
                        }
                    }
                }
            }
        },
    },
)
def advanced_search(
    body: AdvancedSearchRequest,
    request: Request,
) -> SearchResponse:
    """Execute an advanced satellite search."""
    return _execute_search(
        body,
        request,
        adapters.advanced_search_to_core_request,
    )


def _execute_search(
    body: SimpleSearchRequest | AdvancedSearchRequest,
    request: Request,
    adapt_request: Callable[
        [SimpleSearchRequest | AdvancedSearchRequest],
        core.SearchRequest,
    ],
    *,
    approximate_budgeted: bool = False,
) -> SearchResponse:
    core_request = adapt_request(body)
    settings = request.app.state.api_settings
    search_kwargs = {"cache_dir": settings.tle_cache_dir}
    if approximate_budgeted:
        search_kwargs["approximate_budgeted"] = True
    parallel_search = _parallel_search_config_from_request(request)
    if parallel_search is not None:
        search_kwargs["parallel_search"] = parallel_search
    core_response = core.search_candidates(core_request, **search_kwargs)
    _persist_named_station_after_success(_station_store_path(request), body.station)
    return adapters.core_response_to_api_response(core_response)


def _parallel_search_config_from_request(
    request: Request,
) -> pass_analysis.ParallelSearchConfig | None:
    settings = request.app.state.api_settings
    if not settings.parallel_search_enabled:
        return None
    return pass_analysis.derive_default_parallel_search_config(
        enabled=True,
        requested_worker_count=settings.parallel_worker_count,
        chunk_size=settings.parallel_chunk_size,
    )


def _persist_named_station_after_success(
    station_store_path: Path,
    station: SearchStation,
) -> None:
    if station.name is None:
        return
    station_store.add_station_if_new(station_store_path, station)


def _station_store_path(request: Request) -> Path:
    return request.app.state.api_settings.station_store_path


__all__ = ["router"]
