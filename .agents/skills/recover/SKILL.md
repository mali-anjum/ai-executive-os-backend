---
name: recover
description: When something goes wrong during a build in the AI Executive OS backend, diagnose what type of failure it is before deciding how to respond. Targeted fix, hard reset, or full rethink — the right response depends on the right diagnosis.
---

Not every problem is a bug. Not every bug needs debugging. When something goes wrong, the instinct is to keep prompting — describe the problem, ask for a fix, get another broken version, repeat. The session gets longer, the context gets polluted, the code gets worse. This skill diagnoses first, then prescribes the right response. Those are two separate steps and cannot be swapped.

## Project Grounding — the common ways this backend repo goes wrong

Knowing these recurring failure patterns lets you diagnose fast:

- **Wrong layer.** Business logic in a router, auth in an agent or task, DB access from a router, `os.environ` scattered instead of `app.core.config.settings`. The strict layer table in `context/code-desing-patterns.md §1` governs what each layer may import.
- **Schema drift.** Alembic revisions or dashboard-only edits instead of `supabase/migrations/*.sql`; a migration added without its `app/models/db/tables.py` mirror, RLS policy, or FK index.
- **Duplicate code.** A second service/router/schema/flag created when one already exists (check the inventories — there are already `app/services/`, `app/api/v1/routers/`, `app/models/http/`, `config/features.json`).
- **Broken tenancy.** A query not scoped to `org_id`, or a route missing `tenant_org_id` / `require_admin` — a cross-org leak. Authoritative RLS (`auth_org_id()`) is the backstop, but the router must still pass the correct org.
- **Feature-flag bypass.** Shipping a half-implemented feature instead of gating with HTTP 404 when the flag is disabled.
- **Celery session misuse.** Using `AsyncSessionLocal` instead of `CeleryAsyncSessionLocal` inside a worker task.
- **Async/await misuse.** Blocking calls in async handlers, or `asyncio.run()` in the wrong place (only inside Celery task adapters).

## Step 1 — Describe What Went Wrong

Listen first. Ask:

```text
Describe what is wrong. Be specific:
- What did you expect to happen?
- What happened instead?
- How many times have you tried to fix it already?
- Which file/layer is involved (router, service, agent, task, migration)?
```

Read the answer carefully. The number of fix attempts tells you whether this is a fresh problem or a session that has already gone wrong.

## Step 2 — Identify the Failure Mode

### Failure Mode 1 — A specific thing is broken
**Signs:** isolated, the rest of the app works, first/second attempt, clear error or wrong behaviour.
**What it means:** a normal bug with a root cause. **Response:** Targeted fix — Step 3A.

### Failure Mode 2 — The session has gone wrong
**Signs:** multiple attempts made things worse, fixes patching fixes, polluted context, unclear what the original problem was.
**What it means:** the session is polluted; more prompting compounds the damage. **Response:** Hard reset — Step 3B.

### Failure Mode 3 — The foundation is wrong
The implementation itself misunderstands the architecture. Signs include:
- Code in the **wrong layer** (business logic in a router, auth in an agent/task).
- Schema work done outside `supabase/migrations/`.
- A **duplicate** service/router/schema/flag written when one already exists.
- A tenancy gap (route not org-scoped) or a feature-flag bypass.
- A frontend contract changed without updating `app/models/http/` (the schema mirror).

Fixing pieces will not help — the approach is wrong. **Response:** Rethink — Step 3C.

Tell the developer which mode this is before proceeding:

```text
This looks like Failure Mode [1/2/3] — [name].

[One sentence explaining why.]

Here is how we handle this:
```

## Step 3A — Targeted Fix

For Failure Mode 1. Diagnose before touching code — get the exact error or wrong behaviour, the file and layer, and the contract involved. Identify the root cause and propose a minimal fix:

```text
Root cause: [what is actually wrong and where]
Fix: [the smallest change that resolves it and why]
```

Wait for confirmation before changing anything. If the fix does not work, stop and re-diagnose the root cause — it was probably wrong. After two wrong root-cause diagnoses, re-evaluate: this may actually be Failure Mode 2 or 3.

## Step 3B — Hard Reset

For Failure Mode 2. Acknowledge honestly that a fresh start beats continuing in a polluted context. Save what is worth keeping as a reset note:

```markdown
## Reset Note — [Feature Name]

### What we were building
[Original feature description]

### What went wrong
[Honest summary]

### What to avoid next time
[Specific patterns that failed — e.g. wrong layer, schema outside migrations, duplicated service]

### Starting point for next session
[What to keep, what to discard]
```

Then instruct the developer: save the note, end this session, start fresh, `/remember restore` if memory exists, and re-approach with the reset note as context. Do not continue in this session.

## Step 3C — Rethink

For Failure Mode 3. The approach is wrong, not a bug. Name the wrong assumption in this repo's terms:

```text
The core issue is not a bug — it is a wrong assumption:

Assumed: [what was assumed]
Reality: [what is actually true in this codebase]

This means the current implementation cannot be fixed by patching.
The approach needs to change.
```

Propose the correct approach (right layer, migrations through `supabase/`, reuse an existing service, enforce tenancy + flags), say what must be discarded and what can be kept, and wait for confirmation before rebuilding. Only after confirmation does any rebuilding begin.

## The Principle

The worst thing you can do when something is broken is keep doing the same thing faster. Diagnose first. Respond correctly — and in this backend, make sure fixes respect the strict layers, the migration protocol in `supabase/README.md`, tenancy/RLS, feature flags, and the `code-desing-patterns.md` drift guards.

## Hard Rules — Must Never Violate

1. Before writing a fix, **check what already exists** — never write a second service/router/schema/flag when one exists.
2. Never introduce Alembic, dashboard-only schema edits, or a migration without its `tables.py` mirror + RLS + FK index.
3. Never put business logic in a router or auth in an agent/task/circuit breaker.
4. Never scatter `os.environ` — use `settings` from `app.core.config`.
5. Never use `AsyncSessionLocal` in a Celery worker — use `CeleryAsyncSessionLocal`.
6. Never bypass a feature flag with a half-implementation — gate with HTTP 404 when disabled.
7. After two failed root-cause fixes, re-diagnose (this may be Failure Mode 2 or 3, not Mode 1).

