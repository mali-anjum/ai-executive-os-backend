-- Alembic revision 003: Slack user ids, assignee mappings, tickets.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS slack_user_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS department VARCHAR(64);

CREATE TABLE IF NOT EXISTS public.assignee_mappings (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES public.organizations (id),
    department VARCHAR(64) NOT NULL,
    user_ids JSONB NOT NULL,
    round_robin_index INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_assignee_org_dept UNIQUE (org_id, department)
);

CREATE INDEX IF NOT EXISTS ix_assignee_mappings_org_id ON public.assignee_mappings (org_id);

CREATE TABLE IF NOT EXISTS public.tickets (
    id UUID PRIMARY KEY,
    org_id UUID REFERENCES public.organizations (id),
    source VARCHAR(32) NOT NULL,
    raw_payload JSONB,
    intent VARCHAR(64),
    priority INTEGER,
    summary TEXT,
    department VARCHAR(64),
    assignee_id UUID REFERENCES public.users (id),
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    external_ticket_id VARCHAR(128),
    slack_channel_id VARCHAR(64),
    slack_message_ts VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tickets_org_id ON public.tickets (org_id);
CREATE INDEX IF NOT EXISTS ix_tickets_assignee_id ON public.tickets (assignee_id);
