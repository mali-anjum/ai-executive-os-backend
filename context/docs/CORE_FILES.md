# Core files — where the app logic lives

Use this map when debugging. **Not a `.venv` issue** — Python deps are fine; errors were config + race conditions + dev-mode compile time.

---

## Backend (3 files)

| File | Role |
|------|------|
| [`backend/app/main.py`](../backend/app/main.py) | FastAPI entry: routers (`/api/v1/query`, `/tickets`, `/ingest`, …), CORS, OpenAPI |
| [`backend/app/core/security.py`](../backend/app/core/security.py) | Auth on every API call: Supabase JWT → `AuthContext` → calls tenant sync |
| [`backend/app/core/tenant_sync.py`](../backend/app/core/tenant_sync.py) | Ensures `organizations` + `users` rows exist for JWT `org_id` / `user_id` |

**Also important:** [`backend/app/core/config.py`](../backend/app/core/config.py) (`.env.dev` / `.env.production`), [`backend/app/agents/knowledge_agent.py`](../backend/app/agents/knowledge_agent.py) (RAG chat).

---

## Frontend (3 files)

| File | Role |
|------|------|
| [`frontend/src/proxy.ts`](../frontend/src/proxy.ts) | Next 16 request gate: session check, redirect login ↔ dashboard |
| [`frontend/src/auth/organisms/AuthProvider.tsx`](../frontend/src/auth/organisms/AuthProvider.tsx) | Supabase session in React, wraps the app |
| [`frontend/src/auth/services/auth.service.ts`](../frontend/src/auth/services/auth.service.ts) | Login/signup/logout + attaches Bearer token to API calls |

**Also important:** [`frontend/src/app/layout.tsx`](../frontend/src/app/layout.tsx) (shell, theme), [`frontend/src/common/services/supabase/client.ts`](../frontend/src/common/services/supabase/client.ts) (browser Supabase client).

---

## Start commands

```bash
# Repo root — both apps
pnpm run dev    # backend/.env.dev + frontend/.env.dev
pnpm run prod   # backend/.env.production + frontend/.env.production
```
