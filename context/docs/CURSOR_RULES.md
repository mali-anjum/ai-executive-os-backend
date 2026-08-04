# 10. cursor.md — AI Code Generation Rules

> **Canonical file:** [`../cursor.md`](../cursor.md) at the **repository root**.  
> Cursor reads `cursor.md` from the repo root automatically. This doc is a readable copy for the `docs/` index.

Copy or sync from root `cursor.md` when updating rules.

---

## Project

**AI-Powered Executive Operating System & SOP Automator**

---

## Architecture rules (never violate)

- Frontend uses **Atomic Design:** `atoms/` → `molecules/` → `organisms/` → `templates/`.
- Atoms are stateless. Molecules have local state only. Organisms use **hooks** for data.
- **Redux Toolkit** for global state — components MUST use hooks (`useChat`, `useUser`, etc.), never import `store/` directly.
- Backend: **router → service → database/agents**. Routers have no business logic.
- Services never import FastAPI `Request`/`Response` (except auth/rate-limit modules).
- **LangGraph** agents are deterministic state machines with explicit named nodes.
- Every new feature is gated by **`frontend/src/config/features.config.ts`** and **`FEATURE_*`** env vars.
- Database queries filter by **`org_id`** for multi-tenant isolation.

---

## Tech stack (use only these)

| Layer | Stack |
|-------|--------|
| Frontend | **Next.js 16** (App Router), TypeScript, Tailwind CSS, Redux + hooks |
| Auth | **Supabase Auth** — not NextAuth, not Zustand |
| Backend | Python 3.11+, FastAPI, LangGraph, LangChain splitters, SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 + pgvector, Alembic migrations |
| LLM | GPT-4o (generate), gpt-4o-mini (grade), text-embedding-3-small (embed) |
| Queue | Celery + Redis — never ingest documents synchronously in routes |

*PDF master guide mentions Next.js 14 / Shadcn / Zustand — **do not use** in this repo.*

---

## Code style

- Python: type hints, Black-compatible layout.
- TypeScript: `strict`, no `any`.
- Pydantic schemas on all API request/response bodies.
- Docstrings on non-obvious service methods only.

---

## Testing

- Service methods: pytest — happy, empty, error (`AsyncMock` for async).
- Atoms/molecules: Jest + React Testing Library when needed.
- No `time.sleep()` — use `pytest-asyncio`.

---

## Security

- Never log API keys, passwords, or JWTs.
- Validate inputs with Pydantic.
- Webhooks: verify Slack HMAC before processing.
- DB-stored integration secrets: Fernet + `ENCRYPTION_KEY`.

---

See also: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md), [PROJECT_MASTER.md](./PROJECT_MASTER.md).
