"""Pre-flight env checks — hard-fail in production if secrets or LLM key missing."""

import logging
import sys

from app.core.config import settings

logger = logging.getLogger(__name__)

_REQUIRED_PRODUCTION = (
    "database_url",
    "redis_url",
    "encryption_key",
)


def validate_environment(*, production: bool = False) -> list[str]:
    errors: list[str] = []

    if production:
        for field in _REQUIRED_PRODUCTION:
            if not getattr(settings, field, ""):
                errors.append(f"Missing required setting: {field.upper()}")

        if settings.cors_origins == "http://localhost:3000":
            logger.warning(
                "CORS_ORIGINS still uses localhost default in production mode"
            )

    from app.core.llm_registry import validate_active_provider

    errors.extend(validate_active_provider())

    return errors


def run_startup_validation() -> None:
    production = settings.app_env.lower() in ("production", "prod")
    errors = validate_environment(production=production)
    if errors:
        for err in errors:
            logger.error("startup_validation: %s", err)
        if production:
            sys.exit(1)
