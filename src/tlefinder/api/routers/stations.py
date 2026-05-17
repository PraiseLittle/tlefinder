"""Station persistence routes for the TLE Finder API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from tlefinder.api import station_store
from tlefinder.api.schemas import (
    ErrorResponse,
    StationListRequest,
    StationListResponse,
)

router = APIRouter(tags=["stations"])

_STATION_LIST_EXAMPLE = {
    "stations": [
        {
            "name": "Paris Observatory",
            "latitude": 48.8367,
            "longitude": 2.3365,
            "elevation_m": 67.0,
        }
    ]
}

_ERROR_EXAMPLE = {
    "error": {
        "code": "station_store_error",
        "message": "Station store operation failed.",
        "details": {},
        "field_errors": [],
    }
}

_STATION_ERROR_RESPONSES = {
    422: {
        "model": ErrorResponse,
        "description": "Station request validation failed.",
        "content": {
            "application/json": {
                "examples": {
                    "station_validation_error": {
                        "summary": "Invalid station replacement",
                        "value": {
                            "error": {
                                "code": "station_validation_error",
                                "message": "Station list validation failed.",
                                "details": {},
                                "field_errors": [
                                    {
                                        "field": "stations.1",
                                        "message": (
                                            "duplicate physical station matches "
                                            "stations.0"
                                        ),
                                    }
                                ],
                            }
                        },
                    }
                }
            }
        },
    },
    500: {
        "model": ErrorResponse,
        "description": "Station store operation failed.",
        "content": {
            "application/json": {
                "examples": {
                    "station_store_error": {
                        "summary": "Persistence failure",
                        "value": _ERROR_EXAMPLE,
                    }
                }
            }
        },
    },
}


@router.get(
    "/stations",
    response_model=StationListResponse,
    responses=_STATION_ERROR_RESPONSES,
    openapi_extra={
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "examples": {
                            "station_list": {
                                "summary": "Persisted stations",
                                "value": _STATION_LIST_EXAMPLE,
                            }
                        }
                    }
                }
            }
        }
    },
)
def get_stations(request: Request) -> StationListResponse:
    """Return the persisted optical ground station list."""
    stations = station_store.load_stations(_station_store_path(request))
    return StationListResponse(stations=stations)


@router.put(
    "/stations",
    response_model=StationListResponse,
    responses=_STATION_ERROR_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "station_list": {
                            "summary": "Complete station list",
                            "value": _STATION_LIST_EXAMPLE,
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
                            "station_list": {
                                "summary": "Persisted stations",
                                "value": _STATION_LIST_EXAMPLE,
                            }
                        }
                    }
                }
            }
        },
    },
)
def put_stations(
    body: StationListRequest,
    request: Request,
) -> StationListResponse:
    """Replace the complete persisted optical ground station list."""
    stations = station_store.replace_stations(
        _station_store_path(request),
        body.stations,
    )
    return StationListResponse(stations=stations)


def _station_store_path(request: Request) -> Path:
    return request.app.state.api_settings.station_store_path


__all__ = ["router"]
