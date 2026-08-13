---
name: review
description: After building a feature in the AI Executive OS backend, verify it matches the plan, respects this repo's architecture and standards, and is production ready. Reports issues clearly so the developer decides what to fix.
---

Building is not done when the code runs. It is done when the code is **correct** — matches the plan and respects this backend's architecture. AI moves fast and drifts: code that works on the surface but violates the strict layers, the migration protocol, tenancy, auth, or feature flags. This skill catches that before it compounds.

This skill does not fix anything. It reports findings and lets the developer decide.

## Step 1 — Understand What Should Have Been Built

Read in order: the `/architect` plan if one exists, the feature description, and the relevant context (`AGENTS.md`, `context/code-desing-patterns.md`, `supabase/README.md`, `context/docs/PROJECT_MASTER.md`). You cannot verify correctness without knowing what correct looks like. If no plan exists, ask the developer to describe the feature first.

## Step 2 — Review in Three Layers

### Layer 1 — Does it match the plan?
Compare what was built against what was planned: every part present? decisions reflected? scope respected?

### Layer 2 — Does it respect the system?
Where AI drift most commonly happens. Check this repo's hard rules:

- **Strict layers** (`code-desing-patterns.md §1`): router thin (~10-40 lines/handler); business logic in service; DB access in service not router; auth in `security.py` deps not agent/task; core imports only stdlib + third-party.
- **Migrations** (`supabase/README.md`): every schema change is a `supabase/migrations/*.sql`; never Alembic, never dashboard edits; ORM `tables.py` mirrors migration SQL; new tables have RLS + FK index.
- **Tenancy** : every tenant-owned query scoped to `org_id`; route uses `tenant_org_id` / `require_admin`; RLS (`auth_org_id()`) on new tables.
- **Feature flags**: new features gated via `config/features.json` + `feature_registry.py`; disabled routes return HTTP 404; no half-implementations.
- **HTTP contracts**: frontend-facing models live in `app/models/http/` (`schemas.py`, `errors.py`, `stream.py`, `enums.py`); no duplicate schemas.
- **Config**: env read only in `app/core/config.py` (`settings`); no scattered `os.environ`.
- **Celery**: tasks in `app/tasks/`, thin bridges to services, use `CeleryAsyncSessionLocal` in workers, queued via `.delay()` from routers.
- **Naming**: routers `<domain>.py` with `APIRouter()`; services `<domain>_service.py` class `<Domain>Service`; tests `tests/unit/test_<module>.py`; module docstring = one-sentence purpose.

### Layer 3 — Is it production ready?
- Error handling — registered in `app/core/exception_handlers.py`; every failure returns `ApiErrorResponse`; routers raise `HTTPException` for client errors; external API failures (Slack, Jira, LLM) caught in the service with structured fallback.
- Tenancy/security — no cross-org data exposure; tokens/logs never leak (see `_mask_authorization`).
- Async correctness — no blocking calls in async handlers; `asyncio.run()` only in Celery task adapters.
- Edge cases — empty results, disabled feature, missing org, rate limits, LLM failures.

## Step 3 — Report What You Found

```markdown
## Review — [Feature Name]

### Layer 1 — Plan alignment
[PASS / ISSUES FOUND] + list

### Layer 2 — System integrity
[PASS / ISSUES FOUND] + architecture/design/standard violations

### Layer 3 — Production readiness
[PASS / ISSUES FOUND] + error handling / tenancy-security / async / edge cases

### Summary
[X] issues across [Y] layers. Label each with severity.
```

## Step 4 — Let the Developer Decide

Stop after presenting the report. Do not fix anything or suggest fixes unless asked. The developer owns the quality decision; you inform it.

## Severity Guide

- **Critical — fix before moving on:** wrong-layer code (business logic in router, auth in agent/task), schema drift (Alembic/dashboard/migration without `tables.py` + RLS), tenancy gap, duplicate service/router/schema/flag, silent failure.
- **Important — fix soon:** naming/standard violations, missing edge cases, feature-flag not gated, missing error handling for external APIs.
- **Minor — fix when convenient:** non-behavioural inconsistencies, style nits.

## The Standard

The question this skill answers is not "does it work?" — it is "is it correct?" Working and correct are not the same thing. Review exists to catch the difference before it drifts.

## Hard Rules — Must Never Violate (checked in Layer 2)

**No duplicate code — the feature must reuse what already exists.** Before accepting a feature, verify it did not reinvent an existing building block. Check against the existing inventory:

- **Services** (`app/services/*_service.py`): `analytics`, `assignee`, `chunking`, `citation_parser`, `confidence`, `connector`, `demo_seed`, `document_access`, `document_parser`, `document`, `embedding`, `escalation`, `evaluation_harness`, `evaluation`, `executive_summary`, `grading`, `integration_settings`, `intent`, `jira`, `llm`, `notification`, `query_expansion`, `rag_context`, `rerank`, `slack_qa`, `ticket`, `vector`.
- **Routers** (`app/api/v1/routers/`): `analytics`, `connectors`, `demo`, `evaluation`, `health`, `ingest`, `profile`, `query`, `settings`, `tickets`, `webhooks`.
- **Core modules** (`app/core/`): `config`, `database`, `security`, `feature_flags`, `feature_registry`, `llm_registry`, `tenant_sync`, `supabase_jwt`, `exception_handlers`, `rate_limit`, `redis_client`, `encryption`, `cache`, `telemetry`.
- **Agents:** `knowledge_agent`, `project_agent`. **Celery tasks:** `connector_tasks`, `document_tasks`, `slack_tasks`.

If the feature created a second service/router/schema/flag when one already existed, flag as **Critical**.

**Golden-rule violations to flag (all Critical):**
1. Schema via Alembic or dashboard — `supabase/migrations/*.sql` only; `tables.py` mirror + RLS + FK index present.
2. Business logic in a router, or auth in an agent/task — wrong layer.
3. Scattered `os.environ` — must use `settings` from `app.core.config`.
4. `AsyncSessionLocal` used in a Celery worker instead of `CeleryAsyncSessionLocal`.
5. A route not org-scoped (`tenant_org_id`) or missing required RBAC (`require_admin`).
6. A feature shipped without a `config/features.json` flag gated by HTTP 404.
7. A frontend contract changed without updating `app/models/http/`.
8. New HTTP schema duplicated instead of extending `schemas.py`/`errors.py`/`stream.py`.

