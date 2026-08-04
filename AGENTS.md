# Backend agent instructions

**Before any backend change, read:**

1. [`../context/code-desing-patterns.md`](../context/code-desing-patterns.md) — **mandatory** architecture, layers, and drift guards
2. [`../context/progress.md`](../context/progress.md) — current migration/initiative status
3. [`../supabase/README.md`](../supabase/README.md) — database migration protocol

## Hard rules

- **Schema:** `supabase/migrations/` only — never Alembic, never dashboard-only edits
- **Layers:** routers → services → models (see design patterns §1)
- **Config:** `app/core/config.py` only — no scattered `os.environ`
- **Auth:** `app/core/security.py` — not in agents or tasks

## Quick commands

```bash
cd backend
pnpm run db:migrate          # apply Supabase SQL to .env.dev DB
pnpm run test:unit           # pytest
pnpm run typecheck           # pyright
```
