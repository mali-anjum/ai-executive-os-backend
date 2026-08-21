# Agent Instructions — AI Executive OS (backend)

You are working in the **backend repo of AI Executive OS** (`ai-executive-os-backend`):
FastAPI + Celery + Supabase (Postgres / RLS / Auth). The frontend is a **separate
private repo** (`ai-executive-os`). Read this file first and comply with every rule
below — never write code that violates these boundaries.

**Before any backend change, read:**

1. [`.agents/STATE.md`](.agents/STATE.md) — the living state file (always read first, via `/remember restore`)
2. [`context/code-desing-patterns.md`](context/code-desing-patterns.md) — **mandatory** architecture, layers, and drift guards
3. [`supabase/README.md`](supabase/README.md) — database migration protocol

## Hard rules (never break)

- **Schema:** `supabase/migrations/` only — never Alembic, never dashboard-only edits.
- **Layers:** routers → services → models (see design patterns §1).
- **Config:** `app/core/config.py` only — no scattered `os.environ`.
- **Auth/RBAC:** `app/core/security.py` only — not in agents or tasks.
- **Org layer is Supabase-native:** org bootstrap / invitations / membership /
  settings are owned by RLS + PostgREST (migrations `0009`/`0010`/`0011`). Do **not**
  add FastAPI org CRUD endpoints — FastAPI keeps only LLM/RAG, tickets, analytics,
  integrations, and webhooks.
- **Every tenant-owned table** must have an `org_id` column + an `auth_org_id()` RLS policy.

## Skills (in `.agents/skills/`)

Repo-specific runbooks — invoke with `/architect`, `/recover`, `/remember`,
`/review`, `/imprint`. Use `/remember save` at the end of every session and
`/remember restore` at the start of the next so nothing is lost between sessions.

## Quick commands (run from the repo root)

## Backend Testing Standard — Building Stage

Backend tests are maintained in the centralized `tests/` directory:
```text
tests/
├── unit/
├── integration/
├── ai/
└── conftest.py
```

1. Unit tests: test isolated business logic, services, utilities, validation, security logic, and state transformations.
2. Integration tests: test APIs, database behavior, external integrations, authentication/authorization, and multi-tenancy.
3. Security-sensitive behavior must have tests.
4. Multi-tenant boundaries must be tested to prevent cross-organization data access.
5. External integrations such as Slack must test validation, failures, retries, and duplicate events.
6. AI behavior should have evaluation tests/datasets for important classification, summarization, and decision-making behavior.
7. Do not test trivial code merely for coverage.
8. Every important new backend behavior should have an appropriate test.
9. When modifying existing behavior, update the existing tests or add regression tests where necessary.
10. Tests must verify expected behavior and failure behavior.
11. Prefer deterministic tests; mock external services where appropriate.
12. AI-generated backend code must not be considered correct until relevant tests, type/static checks, and linting pass.
13. Do not modify a test simply to make incorrect implementation pass. Tests represent the intended behavior.


```bash
pnpm run db:migrate          # apply Supabase SQL to .env.dev DB
pnpm run test:unit           # pytest
pnpm run typecheck           # pyright
pnpm run dev                 # API + worker (dev, sources .env.dev)
```

