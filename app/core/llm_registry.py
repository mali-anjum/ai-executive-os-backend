"""
Which LLM provider is active and whether its API key is set.

features.json picks openai | gemini | groq | anthropic; startup validation fails
in production if the active provider has no key. Chat + ticket classify both use this.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.core.feature_registry import VALID_AI_PROVIDERS, get_ai_model_config, get_ai_provider
from app.models.http.enums import AiProviderId
from app.models.http.llm import AiProviderPlugin, AiProviderStatus
from app.models.internal.coerce import as_ai_provider_id

logger = logging.getLogger(__name__)

_API_KEY_FIELDS: dict[AiProviderId, str] = {
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
    "gemini": "gemini_api_key",
    "groq": "groq_api_key",
}


def resolve_active_chat_provider_id() -> AiProviderId:
    return get_ai_provider()


def get_active_plugin() -> AiProviderPlugin:
    pid = get_ai_provider()
    cfg = get_ai_model_config(pid)
    return AiProviderPlugin(
        id=pid,
        label=cfg.name,
        chat_model=cfg.chat_model,
        grading_model=cfg.grading_model,
    )


def list_provider_status() -> list[AiProviderStatus]:
    active = get_ai_provider()
    out: list[AiProviderStatus] = []
    for pid_raw in sorted(VALID_AI_PROVIDERS):
        pid = as_ai_provider_id(pid_raw)
        cfg = get_ai_model_config(pid)
        field = _API_KEY_FIELDS[pid]
        out.append(
            AiProviderStatus(
                id=pid,
                label=cfg.name,
                configured=bool(getattr(settings, field, "")),
                active=pid == active,
                chat_model=cfg.chat_model,
            )
        )
    return out


def validate_active_provider() -> list[str]:
    errors: list[str] = []
    pid = get_ai_provider()
    field = _API_KEY_FIELDS.get(pid)
    if (
        settings.app_env.lower() in ("production", "prod")
        and field
        and not getattr(settings, field, "")
    ):
        env_key = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
        }[pid]
        errors.append(f"{env_key} required for ai_provider={pid} in production")
    return errors
