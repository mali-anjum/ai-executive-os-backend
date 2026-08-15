-- Sprint 4 decision — Supabase-native organization layer (hybrid).
--
-- Supabase (Auth + Postgres + RLS) owns the org layer: bootstrap, invitations,
-- membership, settings. FastAPI keeps only compute/secrets (RAG/LLM, tickets,
-- analytics, integrations). This migration adds the pieces Supabase needs so the
-- org layer can be driven from the client (PostgREST + RLS) instead of FastAPI.
--
-- 1. on_auth_user_created trigger: create organization + owner membership from
--    user_metadata at signup (replaces client/FastAPI bootstrap).
-- 2. accept_org_invitation(org_id) SECURITY DEFINER RPC: move the authenticated
--    user into the invited org (RLS must not let a client edit its own org_id).
-- 3. Fix organizations UPDATE policy to allow owner AND admin (was admin-only).

-- 1. Owner + org bootstrap -----------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_meta      jsonb := COALESCE(NEW.raw_user_meta_data, '{}'::jsonb);
    v_org_id    uuid  := NULLIF(v_meta->>'org_id', '')::uuid;
    v_role      text  := COALESCE(NULLIF(v_meta->>'role', ''), 'employee');
    v_org_name  text  := COALESCE(NULLIF(v_meta->>'org_name', ''), 'Organization');
BEGIN
    -- Non-org signups (e.g. a user accepting an invite) are handled by the RPC.
    IF v_org_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Only bootstrap a BRAND-NEW org here. If v_org_id already exists this is a
    -- self-claimed org (privilege-escalation risk) — do NOT attach; the user must
    -- join via accept_org_invitation() with a matching invite.
    IF EXISTS (SELECT 1 FROM public.organizations WHERE id = v_org_id) THEN
        RETURN NEW;
    END IF;

    INSERT INTO public.organizations (id, name)
    VALUES (v_org_id, v_org_name);

    -- First member of a new org is its owner (overrides any client-claimed role).
    v_role := 'owner';

    -- public.users columns (per 0001): id, email, role, org_id, created_at.
    INSERT INTO public.users (id, email, role, org_id)
    VALUES (
        NEW.id,
        COALESCE(NEW.email, ''),
        v_role,
        v_org_id
    )
    ON CONFLICT (id) DO UPDATE
        SET org_id = v_org_id,
            role   = v_role,
            email  = COALESCE(NEW.email, users.email);

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 2. Accept an invitation (move the caller into the invited org) ----------------------------
CREATE OR REPLACE FUNCTION public.accept_org_invitation(p_org_id uuid)
RETURNS TABLE (org_id uuid, org_name text, role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id uuid;
    v_email   text;
    v_inv     public.organization_invitations%ROWTYPE;
    v_role    text;
BEGIN
    v_user_id := auth.uid();
    IF v_user_id IS NOT NULL THEN
        SELECT email INTO v_email FROM auth.users WHERE id = v_user_id;
    END IF;

    -- Only a pending, unexpired invitation for THIS user's email in THIS org.
    IF v_email IS NOT NULL THEN
        SELECT * INTO v_inv
        FROM public.organization_invitations
        WHERE org_id = p_org_id
          AND lower(email) = lower(v_email)
          AND status = 'pending'
          AND expires_at > now()
        LIMIT 1;
    END IF;

    -- Membership move: set the user's org_id + role from the invitation.
    IF v_inv.id IS NOT NULL THEN
        v_role := v_inv.role;

        INSERT INTO public.users (id, email, role, org_id)
        VALUES (v_user_id, v_email, v_role, p_org_id)
        ON CONFLICT (id) DO UPDATE
            SET org_id = p_org_id,
                role   = v_role,
                email  = v_email;

        UPDATE public.organization_invitations
           SET status = 'accepted', accepted_at = now()
         WHERE id = v_inv.id;
    END IF;

    -- Return the resulting org + role only when the accept actually happened.
    RETURN QUERY
    SELECT o.id, o.name, v_role
    FROM public.organizations o
    WHERE o.id = p_org_id
      AND v_inv.id IS NOT NULL;
END;
$$;

-- 3. Fix org UPDATE policy to include owner (owner == admin authority) ------------------------
DROP POLICY IF EXISTS organizations_update ON public.organizations;
CREATE POLICY organizations_update ON public.organizations
    FOR UPDATE TO authenticated
    USING (id = public.auth_org_id() AND public.auth_user_role() IN ('owner', 'admin'))
    WITH CHECK (id = public.auth_org_id());
