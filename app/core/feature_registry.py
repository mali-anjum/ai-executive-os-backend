"""Loads features.json — toggles UI modules and picks the active LLM provider."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from app.core.config import settings
from app.models.http.enums import AiProviderId
from app.models.http.features import FeaturesPublicConfig
from app.models.http.llm import AiModelConfig

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "features.json"
VALID_AI_PROVIDERS = frozenset({"openai", "gemini", "groq", "anthropic"})

# Optional .env override: FEATURE_DOCUMENT_UPLOAD_ENABLED=false
_ENV_PREFIX = "FEATURE_"


@lru_cache
def _load() -> dict[str, Any]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def is_enabled(name: str) -> bool:
    """Feature on/off — used by API routes and mirrors UI visibility."""
    env_key = f"{_ENV_PREFIX}{name}"
    if env_key in os.environ:
        return _parse_bool(os.environ[env_key])
    features = _load().get("features", {})
    return _parse_bool(features.get(name, False))


def get_ai_provider() -> AiProviderId:
    """
    Which AI vendor runs chat + grading.
    Override: LLM_PROVIDER or AI_PROVIDER in .env
    """
    for env_name in ("LLM_PROVIDER", "AI_PROVIDER"):
        if env_name in os.environ:
            value = os.environ[env_name].strip().lower()
            if value in VALID_AI_PROVIDERS:
                return cast(AiProviderId, value)
    if settings.llm_provider and settings.llm_provider.lower() in VALID_AI_PROVIDERS:
        return cast(AiProviderId, settings.llm_provider.lower())
    value = str(_load().get("ai_provider", "gemini")).strip().lower()
    return cast(AiProviderId, value if value in VALID_AI_PROVIDERS else "gemini")


def _resolve_provider(provider: AiProviderId | str | None) -> AiProviderId:
    if provider is None:
        return get_ai_provider()
    key = provider if isinstance(provider, str) else provider
    lowered = key.lower() if isinstance(key, str) else key
    if lowered in VALID_AI_PROVIDERS:
        return cast(AiProviderId, lowered)
    return get_ai_provider()


def get_ai_model_config(provider: AiProviderId | str | None = None) -> AiModelConfig:
    pid = _resolve_provider(provider)
    models = _load().get("ai_models", {})
    if pid not in models:
        return AiModelConfig(name=pid, chat_model="", grading_model="")
    raw = models[pid]
    return AiModelConfig(
        name=raw.get("name", pid),
        chat_model=raw.get("chat_model", ""),
        grading_model=raw.get("grading_model", ""),
    )


def get_public_config() -> FeaturesPublicConfig:
    """Payload for GET /api/v1/config/features (frontend + documentation)."""
    features = _load().get("features", {})
    resolved = {name: is_enabled(name) for name in features}
    provider = get_ai_provider()
    model = get_ai_model_config(provider)
    return FeaturesPublicConfig(
        ai_provider=provider,
        ai_model_name=model.name,
        ai_chat_model=model.chat_model,
        features=resolved,
    )


def clear_cache() -> None:
    _load.cache_clear()
