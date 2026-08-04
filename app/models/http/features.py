"""Typed feature-flag payload for GET /api/v1/config/features."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.http.enums import AiProviderId


class FeaturesPublicConfig(BaseModel):
    ai_provider: AiProviderId
    ai_model_name: str
    ai_chat_model: str
    features: dict[str, bool] = Field(default_factory=dict)
