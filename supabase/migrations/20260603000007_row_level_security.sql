-- Row Level Security: org-scoped access for authenticated Supabase users.
-- FastAPI uses a direct Postgres connection (service role); RLS protects PostgREST / client access.

CREATE OR REPLACE FUNCTION public.auth_org_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        NULLIF(auth.jwt() -> 'user_metadata' ->> 'org_id', '')::uuid,
        NULLIF(auth.jwt() -> 'app_metadata' ->> 'org_id', '')::uuid
    );
$$;

CREATE OR REPLACE FUNCTION public.auth_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT NULLIF(auth.jwt() ->> 'sub', '')::uuid;
$$;

CREATE OR REPLACE FUNCTION public.auth_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        NULLIF(auth.jwt() -> 'user_metadata' ->> 'role', ''),
        NULLIF(auth.jwt() -> 'app_metadata' ->> 'role', ''),
        'employee'
    );
$$;

-- organizations
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY organizations_select ON public.organizations
    FOR SELECT TO authenticated
    USING (id = public.auth_org_id());

CREATE POLICY organizations_update ON public.organizations
    FOR UPDATE TO authenticated
    USING (id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (id = public.auth_org_id());

-- users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select ON public.users
    FOR SELECT TO authenticated
    USING (org_id = public.auth_org_id() OR id = public.auth_user_id());

CREATE POLICY users_update_self ON public.users
    FOR UPDATE TO authenticated
    USING (id = public.auth_user_id())
    WITH CHECK (id = public.auth_user_id());

CREATE POLICY users_admin_all ON public.users
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (org_id = public.auth_org_id());

-- documents
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_org_select ON public.documents
    FOR SELECT TO authenticated
    USING (org_id = public.auth_org_id() AND deleted_at IS NULL);

CREATE POLICY documents_admin_write ON public.documents
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (org_id = public.auth_org_id());

-- document_chunks (inherit document org scope)
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY document_chunks_select ON public.document_chunks
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.org_id = public.auth_org_id()
              AND d.deleted_at IS NULL
        )
    );

CREATE POLICY document_chunks_admin_write ON public.document_chunks
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.org_id = public.auth_org_id()
        )
        AND public.auth_user_role() = 'admin'
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.org_id = public.auth_org_id()
        )
    );

-- queries
ALTER TABLE public.queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY queries_select ON public.queries
    FOR SELECT TO authenticated
    USING (org_id = public.auth_org_id());

CREATE POLICY queries_insert ON public.queries
    FOR INSERT TO authenticated
    WITH CHECK (org_id = public.auth_org_id() AND user_id = public.auth_user_id());

-- tickets
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY tickets_org_access ON public.tickets
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id())
    WITH CHECK (org_id = public.auth_org_id());

-- assignee_mappings
ALTER TABLE public.assignee_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY assignee_mappings_admin ON public.assignee_mappings
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (org_id = public.auth_org_id());

-- activity_logs
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY activity_logs_select ON public.activity_logs
    FOR SELECT TO authenticated
    USING (org_id = public.auth_org_id());

CREATE POLICY activity_logs_insert ON public.activity_logs
    FOR INSERT TO authenticated
    WITH CHECK (org_id = public.auth_org_id());

-- org_integrations
ALTER TABLE public.org_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_integrations_admin ON public.org_integrations
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (org_id = public.auth_org_id());

-- connector_syncs
ALTER TABLE public.connector_syncs ENABLE ROW LEVEL SECURITY;

CREATE POLICY connector_syncs_admin ON public.connector_syncs
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() = 'admin')
    WITH CHECK (org_id = public.auth_org_id());
