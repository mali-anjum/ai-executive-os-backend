-- Sprint 4 security hardening — close tenant-isolation / privilege-escalation holes.
--
-- Two related problems in the existing RLS setup:
--
-- 1. `users_update_self` (0007) allowed an authenticated user to UPDATE their own
--    `public.users` row with no org_id/role guard:
--
--        UPDATE public.users SET org_id = '<other-org>', role = 'owner' WHERE id = auth.uid();
--
--    Because permissive policies are OR'ed, that policy alone granted the write
--    regardless of the admin policies' WITH CHECK clauses. This migration adds a
--    BEFORE UPDATE trigger that blocks direct (PostgREST) changes to `org_id` and
--    self `role` changes, and tightens `users_update_self`.
--
-- 2. `auth_org_id()` / `auth_user_role()` (0007) trusted the client-editable
--    `user_metadata` JWT claim first. A client can call
--    `supabase.auth.updateUser({ data: { org_id, role } })` to rewrite its own
--    user_metadata, so the RLS "constant" was actually attacker-controlled. The
--    helpers now prefer `app_metadata` (only the service role / SECURITY DEFINER
--    functions can write it), with `user_metadata` kept only as a backwards-
--    compatible fallback. `handle_new_user` and `accept_org_invitation` now write
--    org_id/role into app_metadata, and existing rows are backfilled.

-- =====================================================================================
-- 1. Server-owned tenant identity: read app_metadata first (clients cannot edit it).
-- =====================================================================================

CREATE OR REPLACE FUNCTION public.auth_org_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        NULLIF(auth.jwt() -> 'app_metadata' ->> 'org_id', '')::uuid,
        NULLIF(auth.jwt() -> 'user_metadata' ->> 'org_id', '')::uuid
    );
$$;

CREATE OR REPLACE FUNCTION public.auth_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COALESCE(
        NULLIF(auth.jwt() -> 'app_metadata' ->> 'role', ''),
        NULLIF(auth.jwt() -> 'user_metadata' ->> 'role', ''),
        'employee'
    );
$$;

-- =====================================================================================
-- 2. Block direct (client) changes to org_id / self role on public.users.
-- =====================================================================================

CREATE OR REPLACE FUNCTION public.users_prevent_privilege_escalation()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    -- Only guard untrusted client writes (PostgREST runs as `authenticated`/`anon`).
    -- SECURITY DEFINER functions (accept_org_invitation, handle_new_user) and the
    -- FastAPI service connection run as a trusted role and are intentionally exempt.
    IF current_user IN ('authenticated', 'anon') THEN
        IF NEW.org_id IS DISTINCT FROM OLD.org_id THEN
            RAISE EXCEPTION 'org_id cannot be changed directly; use accept_org_invitation()';
        END IF;
        IF NEW.role IS DISTINCT FROM OLD.role AND OLD.id = public.auth_user_id() THEN
            RAISE EXCEPTION 'you cannot change your own role';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS users_prevent_privilege_escalation ON public.users;
CREATE TRIGGER users_prevent_privilege_escalation
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.users_prevent_privilege_escalation();

-- Tighten the self-update policy: keep org scope in the WITH CHECK as defense in
-- depth (the trigger above is the authoritative guard).
DROP POLICY IF EXISTS users_update_self ON public.users;
CREATE POLICY users_update_self ON public.users
    FOR UPDATE TO authenticated
    USING (id = public.auth_user_id())
    WITH CHECK (id = public.auth_user_id() AND org_id = public.auth_org_id());

-- =====================================================================================
-- 3. Write server-owned org_id/role into app_metadata at bootstrap + invite accept.
-- =====================================================================================

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

    -- Server-owned tenant identity: RLS now reads app_metadata first, so persist
    -- org_id/role where the client cannot overwrite them.
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
     WHERE id = NEW.id;

    RETURN NEW;
END;
$$;

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

        -- Persist the new tenant identity in app_metadata (server-owned).
        UPDATE auth.users
           SET raw_app_meta_data = jsonb_set(
                   jsonb_set(
                       COALESCE(raw_app_meta_data, '{}'::jsonb),
                       '{org_id}',
                       to_jsonb(p_org_id::text)
                   ),
                   '{role}',
                   to_jsonb(v_role)
               )
         WHERE id = v_user_id;
    END IF;

    -- Return the resulting org + role only when the accept actually happened.
    RETURN QUERY
    SELECT o.id, o.name, v_role
    FROM public.organizations o
    WHERE o.id = p_org_id
      AND v_inv.id IS NOT NULL;
END;
$$;

-- =====================================================================================
-- 4. Backfill app_metadata for existing users from the authoritative public.users.
-- =====================================================================================

UPDATE auth.users au
   SET raw_app_meta_data =
           jsonb_set(
               jsonb_set(
                   COALESCE(au.raw_app_meta_data, '{}'::jsonb),
                   '{org_id}',
                   to_jsonb(u.org_id::text)
               ),
               '{role}',
               to_jsonb(u.role)
           )
  FROM public.users u
 WHERE u.id = au.id
   AND u.org_id IS NOT NULL;



