"""Stable JSON error bodies for all API failures (HTTPException, rate limits, validation)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ApiErrorDetail(BaseModel):
    """Single error entry — mirrors FastAPI validation error shape where useful."""

    message: str
    code: str | None = None
    field: str | None = None


class ApiErrorResponse(BaseModel):
    """Every non-2xx response uses this envelope so clients never guess shape."""

    error: ApiErrorDetail
    status_code: int = Field(..., ge=400, le=599)


class HealthStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"


class SlackChallengeResponse(BaseModel):
    challenge: str


class SlackWebhookAck(BaseModel):
    ok: Literal[True] = True
