"""Typed LLM provider registry payloads."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.http.enums import AiProviderId


class AiModelConfig(BaseModel):
    name: str
    chat_model: str
    grading_model: str


class AiProviderPlugin(BaseModel):
    id: AiProviderId
    label: str
    chat_model: str
    grading_model: str


class AiProviderStatus(BaseModel):
    id: AiProviderId
    label: str
    configured: bool
    active: bool
    chat_model: str
