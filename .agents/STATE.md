# STATE — single source of truth (backend repo)

> **The one living file every session reads and updates.** Do **not** create
> sibling memory/state files (`memory.md`, `session.md`, …). Update **this same
> file**: refresh **Current**, append to **Sprint Ledger**, grow **Decisions &
> foundations**, and keep everything **condensed** — prune superseded entries so
> this stays the whole truth, not a transcript.
>
> Read this at the start of every session (`/remember restore`); update it at the
> end (`/remember save`). Secrets never go here — reference `.env.*` file names only.

## Current (latest sprint — refresh each session)

**Sprint 4 — Organization & Multi-Tenant Onboarding.** Built, **not committed**.

- `owner` added as a first-class role (`app/models/http/enums.py` →
  `as_user_role` in `app/models/internal/coerce.py`). `require_admin` /
  `require_leadership` (`app/core/security.py`) treat `owner` as authority.
- **Supabase-native org layer (final):** migrations
  `20260603000009_organization_invitations.sql` (`organization_invitations` +
  org-scoped RLS) and `20260603000010_supabase_native_org.sql` (`handle_new_user`
  trigger, `accept_org_invitation()` SECURITY DEFINER RPC, org-UPDATE RLS
  owner/admin) own bootstrap / invitations / membership / settings.
- **FastAPI org duplicate REMOVED:** `app/api/v1/routers/orgs.py`,
  `app/services/organization_service.py`, `app/core/rbac.py`, the
  `OrganizationInvitation` model, the org HTTP schemas
  (`OrganizationResponse`/`OrgContextResponse`/`OrgUpdateRequest`/
  `OnboardingUpdateRequest`/`MemberResponse`/`InvitationCreateRequest`/
  `InvitationResponse`/`AcceptInvitationResponse`), the `InvitationStatus` enum,
  and their tests (`test_rbac.py`, `test_organization_service.py`,
  `test_org_invitations.py`) are deleted. Org authorization is now enforced only
  by RLS (authoritative) + `require_admin`/`require_leadership` in `security.py`.
- Feature flag `ORG_MANAGEMENT_ENABLED` in `config/features.json` +
  `app/core/feature_flags.py`.

### Current state flags
- **All Sprint 4 backend changes are UNCOMMITTED.**
- **DECISION (2026-08-14): Supabase-native org layer.** Supabase owns the org
  layer (bootstrap, invitations, membership, settings) via RLS + PostgREST +
  trigger/RPC; FastAPI keeps LLM/RAG/tickets/analytics/integrations and all the ai related and other logics that cannot be done with the supabase. The
  duplicate FastAPI org endpoints/service/rbac/schemas/model/tests were removed.
- Migrations `0009` + `0010` **not applied** → run `pnpm run db:migrate` before use.
- `pyright app` errors are pre-existing environment issues (missing deps in
  `.venv`, repo-wide `AsyncSession.add` complaint) — not from this work.

## Sprint Ledger (append-only, condensed — newest on top)

### Sprint 4 — Organizations & multi-tenancy
- Owner RBAC fix + centralized `app/core/rbac.py`.
- `organization_invitations` migration + model + full invitation lifecycle
  (create/list/revoke/accept) + org context/settings/onboarding endpoints.
- Membership stays `users.org_id` + `users.role` (no join table — matches
  `MULTI_TENANCY.md`). Onboarding flag stored in `organizations.settings_json.onboarding`.
- **(2026-08-14 decision)** Migration `0010_supabase_native_org.sql` — Supabase-native
  org layer: `handle_new_user()` trigger (org+owner bootstrap) + `accept_org_invitation()`
  SECURITY DEFINER RPC (invite accept / membership move) + org UPDATE policy now owner/admin.
  FastAPI org endpoints (`orgs.py`, `organization_service.py`) deprecated → removal pass
  + frontend repoint to supabase-js after `0010` is applied & validated.

### Sprint 3 & earlier (foundation — unchanged)
- FastAPI app (`app/main.py`), Supabase-native migrations (`supabase/migrations/`,
  Alembic decommissioned), `security.py` JWT/`AuthContext` auth, RLS
  (`0007_row_level_security.sql`, `auth_org_id()/auth_user_role()`), RAG
  KnowledgeAgent + retrieval/citations, Celery tasks, tickets/slack/webhooks,
  analytics/evaluation/connectors, feature registry (`config/features.json`).

## Decisions & foundations (grow, rarely change — the long-lived truth)
- **Supabase is the database + auth + RLS owner; the FastAPI backend is a
  privileged service connection.** RLS protects client/PostgREST access only;
  FastAPI uses a service-role connection and enforces tenancy in
  `security.py` (never trust frontend org ids).
- Membership = `users.org_id` + `users.role`; **no** separate membership table.
- Role hierarchy: owner > admin > manager > employee; owner = admin authority.
  Authoritative org-authorization = RLS + `require_admin`/`require_leadership`
  (`app/core/security.py`); frontend `getRolePermissions` mirrors it (visibility
  only). `app/core/rbac.py` was removed with the FastAPI org endpoints.
- Every tenant-owned resource has `org_id` + an `auth_org_id()` RLS policy.
- Schema changes only in `supabase/migrations/` (never Alembic/dashboard).
- Layers: routers → services → models. Config only in `app/core/config.py`;
  auth only in `app/core/security.py`. Every route declares `response_model`.
- **DECISION (2026-08-14) — Hybrid org layer.** Supabase owns the org layer:
  `on_auth_user_created` trigger (org+owner bootstrap), `organization_invitations`
  CRUD via PostgREST + RLS (owner/admin), `accept_org_invitation()` SECURITY
  DEFINER RPC (move user into org — clients never edit their own `org_id`/`role`),
  org settings/onboarding via RLS-guarded `update`. **Do not add FastAPI endpoints
  for RLS-capable org CRUD.** FastAPI keeps only LLM/RAG/tickets/analytics/
  integrations/webhooks. One row-level authority (RLS) protects both paths.
- Invitation accept returns the resulting org/role so the **client** syncs its
  Supabase `user_metadata` (what RLS reads) — never a client-set org id to join
  an arbitrary org.

## Next session starts with
1. Apply migrations `0009` + `0010` (`pnpm run db:migrate`) and validate
   `handle_new_user` (signup bootstrap) + `accept_org_invitation()` RPC end-to-end.
2. Wire the invitation-accept entry point (invite link/token → target org): the
   RPC takes the invited org's id, but a new user cannot read invitations via
   RLS (no org yet). Resolve via invite token/link before calling the RPC.
3. (Gap) extend `users_admin_all` + `documents_admin_write` RLS to include `owner`
   so owner can manage members/documents via PostgREST without FastAPI.

## Open questions
- (Resolved) FastAPI org endpoints vs Supabase-native org layer → **Supabase-native.**
- `organization_invitations` partial-unique index relies on lower(email) +
  pending status — confirmed normalized at insert; same guard in `accept_org_invitation`.
- RLS admin policies (`users_admin_all`, `documents_admin_write`) are admin-only;
  include `owner` if owners need PostgREST self-service member/document management.
- Trust-model caveat: `auth_org_id()` and `accept_org_invitation()` read
  `user_metadata` from the JWT (client-set at signup). `handle_new_user` hardens
  only the org-*bootstrap* vector (refuses to attach to a pre-existing org); fully
  eliminating JWT-set org_id is an auth-roles refactor for later.

## Hard rules (inherit every session)
- Never persist secrets (.env.*). Supabase migrations only. Every tenant-owned
  table needs `org_id` + RLS. FastAPI layers: routers → services → models.
  Config in `app/core/config.py`; auth in `app/core/security.py`. No business
  logic in routers; no auth in agents/tasks. Reuse existing services/routers/
  flags before creating new ones.

