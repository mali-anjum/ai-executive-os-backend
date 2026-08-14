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
  `require_leadership` (`app/core/security.py`) treat `owner` as authority —
  fixes the pre-existing bug where an org owner failed admin checks.
- Centralized RBAC → new **`app/core/rbac.py`**: `can_manage_members`
  (owner/admin), `can_assign_role` (only owner assigns owner), `is_leadership`.
- Invitation migration → **`supabase/migrations/20260603000009_organization_invitations.sql`**
  (`organization_invitations` table + partial-unique pending index + org-scoped RLS).
- `OrganizationInvitation` model in `app/models/db/tables.py`.
- HTTP schemas (org/invitation/member/onboarding) in `app/models/http/schemas.py` +
  `InvitationStatus` in `enums.py`. Keep the frontend mirror
  (`src/common/types/http/`) in sync — already done this sprint.
- **`app/services/organization_service.py`** (`OrganizationService`): context /
  update_org / onboarding / members / create+list+revoke+accept invitation — all
  scoped by authenticated `auth.org_id`, never a caller-supplied org id. *(Reference
  only under the Sprint 4 decision below — being superceded by Supabase-native.)*
- **`app/api/v1/routers/orgs.py`** (registered in `app/main.py`, tag
  `organizations`): `GET/PATCH /orgs/me`, `PATCH /orgs/me/onboarding`,
  `GET /orgs/me/members`, `POST/GET/DELETE /orgs/me/invitations`, `POST
  /invitations/accept`. Invitation endpoints gated by `ORG_MANAGEMENT_ENABLED`.
*These FastAPI org endpoints are deprecated by the hybrid decision and will be
removed once migration `0010` is applied + the frontend is repointed to
supabase-js; they remain now only as a working reference.*
- Feature flag `ORG_MANAGEMENT_ENABLED` in `config/features.json` +
  `app/core/feature_flags.py`.
- Tests: `tests/unit/test_rbac.py`, `tests/unit/test_organization_service.py`,
  `tests/unit/test_type_coerce.py` (extended), `tests/integration/test_org_invitations.py`.
  Unit suite **71 passed**; new integration **3 passed**.

### Current state flags
- **All Sprint 4 backend changes are UNCOMMITTED.**
- **DECISION (2026-08-14): Hybrid.** Supabase owns the org layer (bootstrap,
  invitations, membership, settings) via RLS + PostgREST + trigger/RPC; FastAPI
  keeps LLM/RAG/tickets/analytics/integrations. Migration
  `20260603000010_supabase_native_org.sql` implements it (owner+org trigger,
  `accept_org_invitation()` SECURITY DEFINER RPC, org-UPDATE RLS now owner/admin).
  FastAPI `orgs.py`/`organization_service.py` are a **working reference only,
  deprecated** → remove once 0010 is applied & the frontend is repointed to Supabase.
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
  RBAC centralized in `app/core/rbac.py`; frontend `getRolePermissions` mirrors it
  (visibility only — authoritative enforcement is backend `require_admin` + RLS).
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
2. Repoint the frontend `src/org/` to supabase-js (PostgREST + RLS) and confirm
   org CRUD + invitation accept (sync `user_metadata`) work; then DELETE the FastAPI
   org endpoints (`orgs.py`, `organization_service.py`) + org schemas/model/tests.
3. (Gap) extend `users_admin_all` + `documents_admin_write` RLS to include `owner`
   so owner can manage members/documents via PostgREST without FastAPI.
4. Confirm `app/models/http/schemas.py` ↔ frontend `src/common/types/http/` mirror
   are in sync after the org endpoints are trimmed.

## Open questions
- (Resolved) FastAPI org endpoints vs Supabase-native org layer → **Supabase-native.**
- `organization_invitations` partial-unique index relies on lower(email) +
  pending status — confirmed normalized at insert; same guard in `accept_org_invitation`.
- RLS admin policies (`users_admin_all`, `documents_admin_write`) are admin-only;
  include `owner` if owners need PostgREST self-service member/document management.

## Hard rules (inherit every session)
- Never persist secrets (.env.*). Supabase migrations only. Every tenant-owned
  table needs `org_id` + RLS. FastAPI layers: routers → services → models.
  Config in `app/core/config.py`; auth in `app/core/security.py`. No business
  logic in routers; no auth in agents/tasks. Reuse existing services/routers/
  flags before creating new ones.

