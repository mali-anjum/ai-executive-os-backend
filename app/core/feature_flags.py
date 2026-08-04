"""
Backend feature gates — same flags as frontend features.config.ts.

Routes return 404 when disabled (e.g. PROJECT_AGENT_ENABLED off → no /tickets).
Source: config/features.json + FEATURE_* env overrides.
"""

from app.core.feature_registry import get_ai_provider, is_enabled


class FeatureFlags:
    """Readable flags from features.json + FEATURE_* env overrides."""
    @property
    def KNOWLEDGE_AGENT_ENABLED(self) -> bool:
        return is_enabled("KNOWLEDGE_AGENT_ENABLED")

    @property
    def DOCUMENT_UPLOAD_ENABLED(self) -> bool:
        return is_enabled("DOCUMENT_UPLOAD_ENABLED")

    @property
    def MULTI_TENANT_ENABLED(self) -> bool:
        return is_enabled("MULTI_TENANT_ENABLED")

    @property
    def ANALYTICS_DASHBOARD_ENABLED(self) -> bool:
        return is_enabled("ANALYTICS_DASHBOARD_ENABLED")

    @property
    def PROJECT_AGENT_ENABLED(self) -> bool:
        return is_enabled("PROJECT_AGENT_ENABLED")

    @property
    def SLACK_WEBHOOK_ENABLED(self) -> bool:
        return is_enabled("SLACK_WEBHOOK_ENABLED")

    @property
    def JIRA_INTEGRATION_ENABLED(self) -> bool:
        return is_enabled("JIRA_INTEGRATION_ENABLED")

    @property
    def EMAIL_WEBHOOK_ENABLED(self) -> bool:
        return is_enabled("EMAIL_WEBHOOK_ENABLED")

    @property
    def WORKLOAD_BALANCING_ENABLED(self) -> bool:
        return is_enabled("WORKLOAD_BALANCING_ENABLED")

    @property
    def AUDIT_LOG_ENABLED(self) -> bool:
        return is_enabled("AUDIT_LOG_ENABLED")

    @property
    def RAG_CACHE_ENABLED(self) -> bool:
        return is_enabled("RAG_CACHE_ENABLED")

    @property
    def CONFIDENCE_ESCALATION_ENABLED(self) -> bool:
        return is_enabled("CONFIDENCE_ESCALATION_ENABLED")

    @property
    def SLACK_QA_ENABLED(self) -> bool:
        return is_enabled("SLACK_QA_ENABLED")

    @property
    def DOCUMENT_RBAC_ENABLED(self) -> bool:
        return is_enabled("DOCUMENT_RBAC_ENABLED")

    @property
    def SSO_ENABLED(self) -> bool:
        return is_enabled("SSO_ENABLED")

    @property
    def CONNECTOR_SYNC_ENABLED(self) -> bool:
        return is_enabled("CONNECTOR_SYNC_ENABLED")

    @property
    def EVALUATION_DASHBOARD_ENABLED(self) -> bool:
        return is_enabled("EVALUATION_DASHBOARD_ENABLED")

    @property
    def TICKET_APPROVAL_ENABLED(self) -> bool:
        return is_enabled("TICKET_APPROVAL_ENABLED")

    @property
    def INTEGRATIONS_SETTINGS_ENABLED(self) -> bool:
        return is_enabled("INTEGRATIONS_SETTINGS_ENABLED")

    @property
    def DEMO_TENANT_ENABLED(self) -> bool:
        return is_enabled("DEMO_TENANT_ENABLED")

    @property
    def RETRIEVAL_TRACE_ENABLED(self) -> bool:
        return is_enabled("RETRIEVAL_TRACE_ENABLED")

    @property
    def ACTIVE_LLM_PROVIDER(self) -> str:
        return get_ai_provider()


flags = FeatureFlags()
