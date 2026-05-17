"""API-specific exception types and error response handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tlefinder.api.schemas import ApiError, ErrorResponse, FieldError
from tlefinder.core import errors as core_errors


@dataclass(frozen=True, slots=True)
class ApiFieldError:
    """Machine-readable validation detail carried by API exceptions."""

    field: str
    message: str


class ApiErrorException(Exception):
    """Base class for expected API failures with stable error metadata."""

    code: ClassVar[str] = "internal_error"
    default_message: ClassVar[str] = "Internal API error."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
        field_errors: list[ApiFieldError] | None = None,
    ) -> None:
        resolved_message = message or self.default_message
        super().__init__(resolved_message)
        self.message = resolved_message
        self.details = details or {}
        self.field_errors = field_errors or []


class StationValidationError(ApiErrorException):
    """Submitted station list failed API station validation."""

    code = "station_validation_error"
    default_message = "Station list validation failed."


class StationStoreError(ApiErrorException):
    """The YAML station store could not be created, loaded, or saved."""

    code = "station_store_error"
    default_message = "Station store operation failed."


def register_exception_handlers(app: FastAPI) -> None:
    """Register machine-readable API exception handlers."""
    app.add_exception_handler(
        RequestValidationError,
        _request_validation_exception_handler,
    )
    app.add_exception_handler(
        core_errors.ValidationError,
        _core_validation_exception_handler,
    )
    app.add_exception_handler(
        StationValidationError,
        _station_validation_exception_handler,
    )
    app.add_exception_handler(
        StationStoreError,
        _station_store_exception_handler,
    )
    app.add_exception_handler(
        core_errors.TleLoadError,
        _tle_load_exception_handler,
    )
    app.add_exception_handler(
        core_errors.TleFreshnessError,
        _tle_freshness_exception_handler,
    )
    app.add_exception_handler(
        core_errors.SearchExecutionError,
        _search_execution_exception_handler,
    )
    app.add_exception_handler(
        core_errors.PropagationError,
        _search_execution_exception_handler,
    )
    app.add_exception_handler(Exception, _unexpected_exception_handler)


async def _request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        422,
        code="validation_error",
        message="Request validation failed.",
        details={"source": "request"},
        field_errors=_request_validation_field_errors(exc),
    )


async def _core_validation_exception_handler(
    request: Request,
    exc: core_errors.ValidationError,
) -> JSONResponse:
    return _error_response(
        422,
        code="validation_error",
        message=str(exc) or "Request validation failed.",
    )


async def _station_validation_exception_handler(
    request: Request,
    exc: StationValidationError,
) -> JSONResponse:
    return _api_exception_response(
        422,
        exc,
    )


async def _station_store_exception_handler(
    request: Request,
    exc: StationStoreError,
) -> JSONResponse:
    return _api_exception_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        exc,
    )


async def _tle_load_exception_handler(
    request: Request,
    exc: core_errors.TleLoadError,
) -> JSONResponse:
    return _error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        code="tle_unavailable",
        message=str(exc) or "Required TLE data could not be loaded.",
    )


async def _tle_freshness_exception_handler(
    request: Request,
    exc: core_errors.TleFreshnessError,
) -> JSONResponse:
    return _error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        code="tle_stale",
        message=str(exc) or "TLE data is stale.",
    )


async def _search_execution_exception_handler(
    request: Request,
    exc: core_errors.SearchExecutionError | core_errors.PropagationError,
) -> JSONResponse:
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="search_execution_error",
        message=str(exc) or "Search execution failed.",
    )


async def _unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="Unexpected internal error.",
    )


def _api_exception_response(
    status_code: int,
    exc: ApiErrorException,
) -> JSONResponse:
    return _error_response(
        status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        field_errors=exc.field_errors,
    )


def _error_response(
    status_code: int,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    field_errors: list[ApiFieldError | FieldError] | None = None,
) -> JSONResponse:
    response = ErrorResponse(
        error=ApiError(
            code=code,  # type: ignore[arg-type]
            message=message,
            details=details or {},
            field_errors=[
                FieldError(field=field_error.field, message=field_error.message)
                for field_error in (field_errors or [])
            ],
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


def _request_validation_field_errors(
    exc: RequestValidationError,
) -> list[ApiFieldError]:
    field_errors: list[ApiFieldError] = []

    for error in exc.errors():
        field_errors.append(
            ApiFieldError(
                field=_format_request_validation_location(error.get("loc", ())),
                message=str(error.get("msg") or "invalid value"),
            )
        )

    return field_errors


def _format_request_validation_location(location: Any) -> str:
    if not isinstance(location, (list, tuple)):
        return str(location) or "request"

    parts = list(location)
    if parts and parts[0] == "body":
        parts = parts[1:]

    if not parts:
        return "body"
    return ".".join(str(part) for part in parts)


__all__ = [
    "ApiErrorException",
    "ApiFieldError",
    "StationStoreError",
    "StationValidationError",
    "register_exception_handlers",
]
