-- Alembic revision 002: organizations, query org scope, activity_logs.

CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'standard',
    settings_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.queries
    ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES public.organizations (id),
    ADD COLUMN IF NOT EXISTS cited_chunk_ids JSONB;

CREATE INDEX IF NOT EXISTS ix_queries_org_id ON public.queries (org_id);

CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES public.users (id),
    org_id UUID REFERENCES public.organizations (id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_activity_logs_user_id ON public.activity_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_activity_logs_org_id ON public.activity_logs (org_id);
