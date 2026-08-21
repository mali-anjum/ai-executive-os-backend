-- Sprint 4 security hardening (cont.) — bootstrap an org for SSO users.
--
-- Migration 0013 made RLS prefer server-owned app_metadata over client-editable
-- user_metadata, and taught handle_new_user() / accept_org_invitation() to write
-- app_metadata. But handle_new_user() only fires on auth.users INSERT. For SSO
-- (Google/Azure) sign-ins the auth.users row is created with no org, and the org
-- is only claimed later in the "complete profile" step
-- (`supabase.auth.updateUser({ data: { org_id, role, ... } })`), which is an
-- UPDATE — so those users never got a server-owned app_metadata row and stayed on
-- the user_metadata fallback.
--
-- This migration extracts the bootstrap into `bootstrap_new_org_owner()` and wires
-- it into an AFTER UPDATE OF raw_user_meta_data trigger so the SSO path bootstraps
-- the org + app_metadata exactly like signup does.

-- =====================================================================================
-- 1. Shared bootstrap: create a brand-new org + owner membership + app_metadata.
-- =====================================================================================

CREATE OR REPLACE FUNCTION public.bootstrap_new_org_owner(
    p_user_id uuid,
    p_email   text,
    p_meta    jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_org_id   uuid := NULLIF(p_meta->>'org_id', '')::uuid;
    v_role     text := COALESCE(NULLIF(p_meta->>'role', ''), 'employee');
    v_org_name text := COALESCE(NULLIF(p_meta->>'org_name', ''), 'Organization');
BEGIN
    IF v_org_id IS NULL THEN
        RETURN;
    END IF;

    -- Refuse to attach to a pre-existing org (privilege-escalation vector); the
    -- user must join via accept_org_invitation() with a matching invite.
    IF EXISTS (SELECT 1 FROM public.organizations WHERE id = v_org_id) THEN
        RETURN;
    END IF;

    INSERT INTO public.organizations (id, name)
    VALUES (v_org_id, v_org_name);

    -- First member of a new org is its owner (overrides any client-claimed role).
    v_role := 'owner';

    INSERT INTO public.users (id, email, role, org_id)
    VALUES (p_user_id, COALESCE(p_email, ''), v_role, v_org_id)
    ON CONFLICT (id) DO UPDATE
        SET org_id = v_org_id,
            role   = v_role,
            email  = COALESCE(p_email, users.email);

    -- Server-owned tenant identity (RLS reads app_metadata first).
    UPDATE auth.users
       SET raw_app_meta_data = jsonb_set(
               jsonb_set(
                   COALESCE(raw_app_meta_data, '{}'::jsonb),
                   '{org_id}',
                   to_jsonb(v_org_id::text)
               ),
               '{role}',
               to_jsonb(v_role)
           )
     WHERE id = p_user_id;
END;
$$;

-- =====================================================================================
-- 2. Signup bootstrap delegates to the shared helper.
-- =====================================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    PERFORM public.bootstrap_new_org_owner(
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
    );
    RETURN NEW;
END;
$$;

-- =====================================================================================
-- 3. SSO "complete profile" (auth.users UPDATE) bootstraps the org too.
-- =====================================================================================

CREATE OR REPLACE FUNCTION public.on_auth_user_metadata_updated()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- React only when the client introduces/changes the claimed org_id (e.g. the
    -- SSO "complete profile" step). Mirrors handle_new_user() for users whose
    -- auth.users row predates their org metadata.
    IF NEW.raw_user_meta_data->>'org_id' IS DISTINCT FROM OLD.raw_user_meta_data->>'org_id' THEN
        PERFORM public.bootstrap_new_org_owner(
            NEW.id,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data, '{}'::jsonb)
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_metadata_updated ON auth.users;
CREATE TRIGGER on_auth_user_metadata_updated
    AFTER UPDATE OF raw_user_meta_data ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.on_auth_user_metadata_updated();
