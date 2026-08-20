-- Sprint 4 — RBAC parity for the `owner` role in PostgREST/RLS.
--
-- Migration 0007 scoped several admin policies to `auth_user_role() = 'admin'`
-- only, which left owners (the highest role) unable to manage members or
-- documents directly through Supabase. Owners carry admin authority (see
-- MULTI_TENANCY.md and app/core/security.py require_admin), so these policies
-- must include `owner` to match the role hierarchy owner > admin > manager >
-- employee.

-- users: owner may manage members in their org too.
DROP POLICY IF EXISTS users_admin_all ON public.users;
CREATE POLICY users_admin_all ON public.users
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() IN ('owner', 'admin'))
    WITH CHECK (org_id = public.auth_org_id());

-- documents: owner may write documents in their org too.
DROP POLICY IF EXISTS documents_admin_write ON public.documents;
CREATE POLICY documents_admin_write ON public.documents
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() IN ('owner', 'admin'))
    WITH CHECK (org_id = public.auth_org_id());
