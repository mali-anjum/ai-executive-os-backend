"""
Central config — which file loads is ENV_FILE (pnpm run dev vs prod).

Wires Postgres, Redis, LLM keys, Slack secrets, CORS, and feature env overrides.
Nothing in the app reads os.environ directly except this module.
"""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = os.getenv("ENV_FILE", ".env.dev")

class Settings(BaseSettings):
    """Single source of truth for DB, Redis, LLM keys, Slack, and feature env overrides."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, extra="ignore", populate_by_name=True
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    cohere_api_key: str = Field(default="", validation_alias="COHERE_API_KEY")
    llm_provider: str = Field(default="gemini", validation_alias="LLM_PROVIDER")
    anthropic_chat_model: str = Field(
        default="claude-sonnet-4-20250514", validation_alias="ANTHROPIC_CHAT_MODEL"
    )
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(
        default="gemini-2.0-flash", validation_alias="GEMINI_CHAT_MODEL"
    )
    gemini_grading_model: str = Field(
        default="gemini-2.0-flash", validation_alias="GEMINI_GRADING_MODEL"
    )
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_chat_model: str = Field(
        default="llama-3.3-70b-versatile", validation_alias="GROQ_CHAT_MODEL"
    )
    groq_grading_model: str = Field(
        default="llama-3.1-8b-instant", validation_alias="GROQ_GRADING_MODEL"
    )
    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(
        default=0.1, validation_alias="SENTRY_TRACES_SAMPLE_RATE"
    )
    rag_cache_ttl_seconds: int = Field(default=3600, validation_alias="RAG_CACHE_TTL_SECONDS")
    # Deprecated: only for projects still on legacy HS256 JWTs. Prefer JWKS via SUPABASE_URL.
    supabase_jwt_secret: str = Field(default="", validation_alias="SUPABASE_JWT_SECRET")
    openai_chat_model: str = Field(default="gpt-4o", validation_alias="OPENAI_CHAT_MODEL")
    openai_grading_model: str = Field(
        default="gpt-4o-mini", validation_alias="OPENAI_GRADING_MODEL"
    )
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = Field(default=100, validation_alias="EMBEDDING_BATCH_SIZE")
    max_chunk_tokens: int = 800
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(
        default="", validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    supabase_storage_bucket: str = Field(
        default="documents", validation_alias="SUPABASE_STORAGE_BUCKET"
    )
    retrieval_top_k: int = 10
    rerank_top_k: int = 5
    min_relevance_grade: int = 3
    upload_dir: str = Field(default="/tmp/uploads", validation_alias="UPLOAD_DIR")
    cors_origins: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGINS")

    feature_knowledge_agent_enabled: bool = True
    feature_document_upload_enabled: bool = True
    feature_multi_tenant_enabled: bool = True
    feature_analytics_dashboard_enabled: bool = True
    feature_project_agent_enabled: bool = Field(default=True, validation_alias="FEATURE_PROJECT_AGENT_ENABLED")
    feature_slack_webhook_enabled: bool = Field(default=True, validation_alias="FEATURE_SLACK_WEBHOOK_ENABLED")
    feature_jira_integration_enabled: bool = Field(
        default=True, validation_alias="FEATURE_JIRA_INTEGRATION_ENABLED"
    )
    feature_email_webhook_enabled: bool = Field(
        default=True, validation_alias="FEATURE_EMAIL_WEBHOOK_ENABLED"
    )
    feature_workload_balancing_enabled: bool = Field(
        default=True, validation_alias="FEATURE_WORKLOAD_BALANCING_ENABLED"
    )
    feature_audit_log_enabled: bool = Field(default=True, validation_alias="FEATURE_AUDIT_LOG_ENABLED")
    feature_custom_llm_provider_enabled: bool = Field(
        default=True, validation_alias="FEATURE_CUSTOM_LLM_PROVIDER_ENABLED"
    )
    feature_rag_cache_enabled: bool = Field(default=True, validation_alias="FEATURE_RAG_CACHE_ENABLED")

    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")

    slack_signing_secret: str = Field(default="", validation_alias="SLACK_SIGNING_SECRET")
    slack_bot_token: str = Field(default="", validation_alias="SLACK_BOT_TOKEN")
    default_org_id: str = Field(default="", validation_alias="DEFAULT_ORG_ID")
    slack_webhook_max_age_seconds: int = 60 * 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_project_url(self) -> str:
        """Project root URL (not Data API /rest/v1). Used for Auth JWKS + issuer."""
        base = self.supabase_url.rstrip("/")
        if base.endswith("/rest/v1"):
            base = base[: -len("/rest/v1")]
        return base

    @property
    def supabase_jwks_url(self) -> str:
        base = self.supabase_project_url
        if not base:
            return ""
        return f"{base}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_jwt_issuer(self) -> str:
        base = self.supabase_project_url
        if not base:
            return ""
        return f"{base}/auth/v1"

    @property
    def redis_url_for_celery(self) -> str:
        """Celery requires ssl_cert_reqs on rediss:// (e.g. Upstash)."""
        url = self.redis_url
        if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}ssl_cert_reqs=CERT_NONE"
        return url

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev", "local")


settings = Settings()