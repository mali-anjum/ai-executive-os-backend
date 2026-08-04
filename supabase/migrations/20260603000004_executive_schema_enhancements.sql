-- Alembic revision 004: executive schema enhancements.

ALTER TABLE public.organizations
    ADD COLUMN IF NOT EXISTS slug VARCHAR(128),
    ADD COLUMN IF NOT EXISTS industry VARCHAR(64),
    ADD COLUMN IF NOT EXISTS logo_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS website VARCHAR(255),
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_slug ON public.organizations (slug);

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS job_title VARCHAR(128),
    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(32),
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(64),
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS preferences_json JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_org_id'
    ) THEN
        ALTER TABLE public.users
            ADD CONSTRAINT fk_users_org_id
            FOREIGN KEY (org_id) REFERENCES public.organizations (id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_users_org_id ON public.users (org_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_documents_org_id'
    ) THEN
        ALTER TABLE public.documents
            ADD CONSTRAINT fk_documents_org_id
            FOREIGN KEY (org_id) REFERENCES public.organizations (id) ON DELETE SET NULL;
    END IF;
END $$;

ALTER TABLE public.documents
    ADD COLUMN IF NOT EXISTS mime_type VARCHAR(128),
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS page_count INTEGER,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_documents_org_status ON public.documents (org_id, status);

ALTER TABLE public.document_chunks
    ADD COLUMN IF NOT EXISTS token_count INTEGER;

ALTER TABLE public.tickets
    ADD COLUMN IF NOT EXISTS title VARCHAR(255),
    ADD COLUMN IF NOT EXISTS created_by_id UUID REFERENCES public.users (id),
    ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS tags JSONB;

CREATE INDEX IF NOT EXISTS ix_tickets_org_status ON public.tickets (org_id, status);
CREATE INDEX IF NOT EXISTS ix_tickets_created_by_id ON public.tickets (created_by_id);

ALTER TABLE public.queries
    ADD COLUMN IF NOT EXISTS session_id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS model VARCHAR(64),
    ADD COLUMN IF NOT EXISTS feedback VARCHAR(16);

CREATE INDEX IF NOT EXISTS ix_queries_org_created ON public.queries (org_id, created_at);

ALTER TABLE public.activity_logs
    ADD COLUMN IF NOT EXISTS metadata_json JSONB;
