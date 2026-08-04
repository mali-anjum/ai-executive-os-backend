-- Baseline schema migrated from Alembic revision 001.
-- Extensions + core tables: users, documents, document_chunks, queries.

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'employee',
    org_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY,
    org_id UUID,
    user_id UUID REFERENCES public.users (id),
    filename VARCHAR(512) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_documents_user_id ON public.documents (user_id);

CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON public.document_chunks (document_id);

CREATE TABLE IF NOT EXISTS public.queries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES public.users (id),
    query_text TEXT NOT NULL,
    answer_text TEXT,
    cited_chunks JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_queries_user_id ON public.queries (user_id);
