-- Organization invitations: Owner/Admin invite a work email into their org.
-- Membership is modeled by users.org_id + users.role (see MULTI_TENANCY.md);
-- an accepted invitation provisions the invited user's org + role.

CREATE TABLE IF NOT EXISTS public.organization_invitations (
    id           UUID PRIMARY KEY,
    org_id       UUID NOT NULL REFERENCES public.organizations (id) ON DELETE CASCADE,
    email        VARCHAR(320) NOT NULL,
    role         VARCHAR(50) NOT NULL DEFAULT 'employee',
    department   VARCHAR(64),
    token        VARCHAR(128) NOT NULL UNIQUE,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending | accepted | revoked | expired
    expires_at   TIMESTAMPTZ NOT NULL,
    invited_by   UUID REFERENCES public.users (id) ON DELETE SET NULL,
    accepted_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_org_invitations_org_id ON public.organization_invitations (org_id);
CREATE INDEX IF NOT EXISTS ix_org_invitations_email ON public.organization_invitations (email);
CREATE INDEX IF NOT EXISTS ix_org_invitations_status ON public.organization_invitations (status);

-- Prevent duplicate pending invitations for the same email in the same org.
CREATE UNIQUE INDEX IF NOT EXISTS ux_org_invitations_pending_email
    ON public.organization_invitations (org_id, lower(email))
    WHERE status = 'pending';

-- RLS: members may read their own org's invitations; only owner/admin may
-- create, update (revoke), or delete them. Scope is always the caller's org.
ALTER TABLE public.organization_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_invitations_select ON public.organization_invitations
    FOR SELECT TO authenticated
    USING (org_id = public.auth_org_id());

CREATE POLICY org_invitations_admin_write ON public.organization_invitations
    FOR ALL TO authenticated
    USING (org_id = public.auth_org_id() AND public.auth_user_role() IN ('owner', 'admin'))
    WITH CHECK (org_id = public.auth_org_id());
