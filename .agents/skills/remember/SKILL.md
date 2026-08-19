---
name: remember
description: Save what matters at the end of a session so the next session in the AI Executive OS backend picks up exactly where you left off. Or restore context at the start of a new session so nothing is lost between them.
---

AI has no memory between sessions. Every new session starts blank. This skill fixes that: `/remember save` at the end of a session, `/remember restore` at the start of a new one.

## Security Boundary

This skill must **never** persist secrets. If any sensitive value appears, do not add it to `.agents/STATE.md`.

Sensitive data includes: API keys, access tokens, refresh tokens, session tokens, passwords, one-time codes, private keys, certificates, cookies, auth headers, connection strings, webhook secrets, and any credential-like value. This repo has real secrets in `.env.dev` and `.env.production` (`DATABASE_URL`, `SUPABASE_*`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ENCRYPTION_KEY`, Slack/Jira tokens) — never capture them.

If a detail is useful but sensitive, store a redacted placeholder (e.g. `[REDACTED_API_KEY]`). If unsure, treat it as sensitive and omit.

## How to Invoke

- `/remember save` — end of session
- `/remember restore` — start of new session
- `/remember` alone — ask which one they need

## Save Mode

Extract only what a developer needs to continue in a fresh context. Not a transcript — the essential state. Be precise with real paths and decisions:

**What was built** — specific files under `app/` (router, service, agent, task, core, model), a `supabase/migrations/<ts>_*.sql`, a new feature flag, or a `config/features.json` change.

**Decisions made** — architectural choices future work depends on: which layer owns the logic, feature-flag choices, auth/RBAC deps used, schema decisions, LLM/vector setup.

**Problems solved** — issues that took time: tenancy/org-isolation bugs, Celery session misuse, async/await pitfalls, JWT/RLS edge cases, duplicate service cleanup.

**Current state** — what works, what is partial, what is known broken.

**What comes next** — the very next thing, specific enough to start immediately.

**Open questions** — anything unresolved.

**What not to capture** — anything visible in the code or docs (`AGENTS.md`, `context/code-desing-patterns.md`, `supabase/README.md`), the build process, or any secret.

Before writing, run a final safety scan for secrets and confirm with the developer. Only write after they say yes.

### Where it lives — one file, the whole truth

There is **one** persistent file: **`.agents/STATE.md`** (project root, beside
`AGENTS.md`). Do **not** create new memory/state files (`memory.md`, `session.md`,
…). That single file is maintained **from the very first sprint to the last** —
each session updates the same file, so it grows and stays the single source of truth.

### Update in place (append + refine, keep it condensed)

- **`## Current (latest sprint)`** — overwrite with this sprint's state: what was
  built (real files, migrations, flags), decisions, current flags (committed vs
  uncommitted, broken vs working).
- **`## Sprint Ledger`** — append a short, condensed entry for this sprint
  (newest on top). Never rewrite history; just add the newest line.
- **`## Decisions & foundations`** — add any new long-lived rule. Keep it tight.
- **`## Next session starts with`** / **`## Open questions`** — refresh each session.

Keep everything **condensed**: prune superseded detail so the file stays the whole
truth, not a transcript. Confirm after writing:

```
State updated in .agents/STATE.md.

Next session: run /remember restore to pick up from here.
```

## Restore Mode

Read **`.agents/STATE.md`** in the project root. If it does not exist, tell the developer it appears to be the first session or the file was not saved.

Read `.agents/STATE.md`, then check only these context files if present: `CLAUDE.md`, `.claude/context.md`, `.github/copilot-instructions.md`, `.cursorrules`, `.cursor/rules/`, `.windsurfrules`, `AGENTS.md`, `.clinerules`, `context.md`. Then read `context/code-desing-patterns.md` and `supabase/README.md` for this repo's rules. Never scan beyond this list.

Never surface raw secrets from restored context — summarise in redacted form only. Remember: this repo's env files hold real credentials; never repeat them.

Summarise what was restored so the developer can verify:

```text
Memory restored. Here is where we are:

**Last session:** [what was built]
**Current state:** [what works right now]
**Decisions in place:** [key decisions locked]
**Next up:** [what the next session should start with]

Is this correct? Say yes to continue, or correct anything first.
```

Do not start building until the developer confirms. If memory is missing important context, say so honestly and let the developer fill the gaps. Do not guess.

## The Rule

Every session ends with `/remember save`. Every session starts with `/remember restore`. Consistent use is the whole system — a skill used sometimes is a skill that cannot be relied on.

## Hard Rules — Must Never Violate

**Capture what already exists so the next session reuses it (no duplication).** The #1 way this backend drifts is the agent forgetting what already exists and writing a duplicate service, router, schema, or flag. Record the **existing** building blocks relevant to this work so the next session does not reinvent them:

- Services: `analytics`, `assignee`, `chunking`, `citation_parser`, `confidence`, `connector`, `demo_seed`, `document_access`, `document_parser`, `document`, `embedding`, `escalation`, `evaluation_harness`, `evaluation`, `executive_summary`, `grading`, `integration_settings`, `intent`, `jira`, `llm`, `notification`, `query_expansion`, `rag_context`, `rerank`, `slack_qa`, `ticket`, `vector` (all `app/services/*_service.py`).
- Routers: `analytics`, `connectors`, `demo`, `evaluation`, `health`, `ingest`, `profile`, `query`, `settings`, `tickets`, `webhooks`.
- Core modules: `config`, `database`, `security`, `feature_flags`, `feature_registry`, `llm_registry`, `tenant_sync`, `supabase_jwt`, `exception_handlers`, `rate_limit`, `redis_client`, `encryption`, `cache`, `telemetry`.
- Agents: `knowledge_agent`, `project_agent`. Celery tasks: `connector_tasks`, `document_tasks`, `slack_tasks`.

Prompts to always answer in saved memory: "Did we reuse an existing service/router/schema/flag or create a new one? What already existed and must not be duplicated next time?"

**Never persist secrets.** No migrations outside `supabase/`, no Alembic/dashboard edits, no business logic in routers, no auth in agents/tasks — these hard rules must be inherited by the next session.

