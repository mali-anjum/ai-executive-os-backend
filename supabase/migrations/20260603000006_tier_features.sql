-- Alembic revision 006: tier features — doc RBAC, confidence, approvals, integrations.

ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS allowed_departments JSONB,
    ADD COLUMN IF NOT EXISTS allowed_roles JSONB,
    ADD COLUMN IF NOT EXISTS source_connector VARCHAR(32);

ALTER TABLE public.queries
    ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS escalated BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS escalation_ticket_id UUID REFERENCES public.tickets (id);

CREATE INDEX IF NOT EXISTS ix_queries_escalation_ticket_id ON public.queries (escalation_ticket_id);

ALTER TABLE public.tickets
    ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS approval_status VARCHAR(32) NOT NULL DEFAULT 'auto_approved',
    ADD COLUMN IF NOT EXISTS approved_by_id UUID REFERENCES public.users (id),
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_tickets_approved_by_id ON public.tickets (approved_by_id);

CREATE TABLE IF NOT EXISTS public.org_integrations (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES public.organizations (id),
    provider VARCHAR(32) NOT NULL,
    config_encrypted TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_org_integration_provider UNIQUE (org_id, provider)
);

CREATE INDEX IF NOT EXISTS ix_org_integrations_org_id ON public.org_integrations (org_id);

CREATE TABLE IF NOT EXISTS public.connector_syncs (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES public.organizations (id),
    connector VARCHAR(32) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    document_id UUID REFERENCES public.documents (id),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    last_synced_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_connector_sync_external UNIQUE (org_id, connector, external_id)
);

CREATE INDEX IF NOT EXISTS ix_connector_syncs_org_id ON public.connector_syncs (org_id);
CREATE INDEX IF NOT EXISTS ix_connector_syncs_document_id ON public.connector_syncs (document_id);
