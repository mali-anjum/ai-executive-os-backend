"""FastAPI OpenAPI `responses=` maps for documented error bodies (not OpenAI)."""

from __future__ import annotations

from typing import Any

from app.models.http.errors import ApiErrorResponse

STANDARD_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ApiErrorResponse, "description": "Bad request"},
    401: {"model": ApiErrorResponse, "description": "Unauthorized"},
    403: {"model": ApiErrorResponse, "description": "Forbidden"},
    404: {"model": ApiErrorResponse, "description": "Not found"},
    422: {"model": ApiErrorResponse, "description": "Validation error"},
    429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ApiErrorResponse, "description": "Server error"},
}
