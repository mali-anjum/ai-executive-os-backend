"""Register typed exception handlers on the FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.models.http.errors import ApiErrorDetail, ApiErrorResponse


def _error_response(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    field: str | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        error=ApiErrorDetail(message=message, code=code, field=field),
        status_code=status_code,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        message = detail
        code = None
        field = None
    elif isinstance(detail, dict):
        message = str(detail.get("message", detail.get("msg", detail)))
        code = detail.get("code") if isinstance(detail.get("code"), str) else None
        field = detail.get("field") if isinstance(detail.get("field"), str) else None
    else:
        message = str(detail)
        code = None
        field = None
    return _error_response(
        status_code=exc.status_code,
        message=message,
        code=code,
        field=field,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = first.get("loc", ())
    field = ".".join(str(part) for part in loc if part != "body") or None
    message = first.get("msg", "Request validation failed")
    return _error_response(
        status_code=422,
        message=str(message),
        code="validation_error",
        field=field,
    )


async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RateLimitExceeded):
        raise exc
    return _error_response(
        status_code=429,
        message=f"Rate limit exceeded: {exc.detail}",
        code="rate_limit_exceeded",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # pyright: ignore[reportArgumentType]
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # pyright: ignore[reportArgumentType]
