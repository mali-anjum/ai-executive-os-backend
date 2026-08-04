# Environment files — quick start

Use **example** files (safe to commit). Copy to the **active** file name (gitignored), then add your secrets.

## Which file you need

| How you run the app | Backend active file | Frontend active file |
|---------------------|---------------------|----------------------|
| **Local (recommended)** — `pnpm run dev` | `backend/.env` ← from `backend/.env.example` | `frontend/.env.local` ← from `frontend/.env.example` |
| **Local — all Docker** | `docker/.env` ← from `docker/.env.local.example` | (frontend vars are inside `docker/.env`) |
| **Production — Docker** | `docker/.env` ← from `docker/.env.production.example` | same `docker/.env` |
| **Production — split deploy** | `backend/.env` ← from `backend/.env.production.example` | `frontend/.env.production` ← from `frontend/.env.production.example` |

## Setup commands (local, no Docker)

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env: GEMINI_API_KEY, ENCRYPTION_KEY, DATABASE_URL, REDIS_URL

pnpm run bootstrap    # Docker Postgres/Redis + venv + migrations (first time)
pnpm run dev          # daily: checks DB, migrates, API (--reload) + Celery

# Frontend
cd ../frontend
cp .env.example .env.local
# Edit: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
pnpm install && pnpm run dev
```

### Backend pnpm scripts

| Command | When to use |
|---------|-------------|
| `pnpm run deps:docker` | Start Postgres + Redis if not already running |
| `pnpm run db:check` | Test `DATABASE_URL` / `REDIS_URL` before starting the API |
| `pnpm run db:migrate` | Run Alembic only |
| `pnpm run dev` | Full local backend (preflight → migrate → API + worker) |
| `pnpm run dev:api` | API only, with preflight + migrate |

Postgres smoke test (must match `DATABASE_URL`):

```bash
PGPASSWORD=postgres psql -h 127.0.0.1 -p 5433 -U postgres -d sop_automator -c "SELECT 1;"
```

## Minimum values to fill (local)

### `backend/.env`

| Variable | Required? |
|----------|-----------|
| `DATABASE_URL` | Yes |
| `REDIS_URL` | Yes |
| `ENCRYPTION_KEY` | Yes (Fernet) |
| `GEMINI_API_KEY` | Yes if `ai_provider` is `gemini` in `config/features.json` |
| `CORS_ORIGINS` | Yes (`http://localhost:3000`) |

### `frontend/.env.local`

| Variable | Required? |
|----------|-----------|
| `NEXT_PUBLIC_API_URL` | Yes |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes |

## AI provider

Set `"ai_provider"` in `backend/config/features.json` (`gemini`, `groq`, `openai`, `anthropic`) and add the matching API key in `backend/.env`.

## All templates in the repo

| Template | Purpose |
|----------|---------|
| `backend/.env.example` | Backend local |
| `frontend/.env.example` | Frontend local |
| `frontend/.env.production.example` | Frontend production build |
| `docker/.env.local.example` | Full stack local Docker |
| `docker/.env.production.example` | Full stack production Docker |

See also: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) · **[DEV_VS_PRODUCTION.md](./DEV_VS_PRODUCTION.md)** (check dev/prod, use `.env.production`)

---

## Start the full app (chat works)

Chat needs **frontend** (UI + Supabase login) + **backend** (API + LLM + DB). Document upload also needs **Celery** (included in `pnpm run dev`).

### Local — three terminals (or two)

**Terminal 1 — data (once per machine, or when Docker was stopped)**

```bash
cd backend
pnpm run deps:docker
```

**Terminal 2 — backend (one command)**

```bash
cd backend
cp .env.example .env          # first time only — fill values below
pnpm run bootstrap             # first time only
pnpm run dev                   # every session: API + Celery + migrate
```

**Terminal 3 — frontend**

```bash
cd frontend
cp .env.example .env.local    # first time only
pnpm install
pnpm run dev
```

**Use the app:** open http://localhost:3000 → sign in with Supabase → open chat → ask a question.

| URL | Service |
|-----|---------|
| http://localhost:3000 | Frontend |
| http://localhost:8000/api/v1/health | API health |
| http://localhost:8000/docs | API docs |

**Alternative — everything in Docker (one command):**

```bash
cp docker/.env.example docker/.env   # fill keys
cd docker
docker compose up --build
```

---

### What to set — local development

#### `backend/.env`

| Variable | Example / notes |
|----------|-----------------|
| `APP_ENV` | `development` (enables dev header auth fallback) |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator` if using `pnpm run deps:docker` (host port **5433** avoids clash with system Postgres on 5432). Or your Supabase pooler URL for hosted DB. |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `ENCRYPTION_KEY` | Generate: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SUPABASE_URL` | Same project URL as frontend (`https://xxx.supabase.co`) — **required** for JWT verification on chat |
| `GEMINI_API_KEY` | Required when `backend/config/features.json` has `"ai_provider": "gemini"` (default) |
| `OPENAI_API_KEY` | Optional; used for embeddings on ingest if set |

#### `frontend/.env.local`

| Variable | Example |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase **anon** key (Settings → API) |

**Supabase user metadata (required for chat auth):** on sign-up, users need `org_id` and `role` in `user_metadata` (the login flow sets this). Backend reads the Supabase JWT + metadata.

**Optional local shortcut (no Supabase session):** with `APP_ENV=development`, API accepts headers `X-Org-Id`, `X-User-Id`, `X-User-Role` — the normal UI still uses Supabase login.

**Meaningful answers:** upload at least one document (ingest uses Celery from `pnpm run dev`).

---

### What to set — production

| Area | File / place | Notes |
|------|----------------|-------|
| Backend env | `backend/.env` or platform secrets | `APP_ENV=production` |
| Frontend env | Host env (e.g. Vercel) | `NEXT_PUBLIC_*` vars — never commit secrets |
| Docker all-in-one | `docker/.env` from `docker/.env.example` | Full stack deploy |

#### Production `backend/.env` (minimum for chat)

| Variable | Notes |
|----------|--------|
| `APP_ENV` | `production` (dev headers **disabled**) |
| `DATABASE_URL` | Hosted Postgres (Supabase, Neon, Railway, …) |
| `REDIS_URL` | Hosted Redis (Upstash, Railway, …) |
| `CORS_ORIGINS` | Your real frontend origin, e.g. `https://app.yourdomain.com` |
| `ENCRYPTION_KEY` | Strong Fernet key; store in secrets manager |
| `SUPABASE_URL` | Same project as frontend |
| LLM key | `GEMINI_API_KEY` / `OPENAI_API_KEY` / etc. per `ai_provider` |

#### Production frontend

| Variable | Notes |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Public API URL, e.g. `https://api.yourdomain.com/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL` | Production Supabase project |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production anon key |

**Deploy commands (typical split deploy):**

```bash
# Backend: migrate then run API + worker on your host
cd backend && alembic upgrade head
# process manager: uvicorn + celery (or use docker compose service api + worker)

# Frontend
cd frontend && pnpm run build && pnpm run start
```

---

### Quick checks if chat fails

```bash
cd backend && pnpm run db:check          # Postgres + Redis reachable
curl http://localhost:8000/api/v1/health
```

- **401 on chat:** not logged in, or `SUPABASE_URL` mismatch / invalid JWT.  
- **500 on chat:** missing LLM API key for `ai_provider`.  
- **Empty answers:** no documents ingested for your `org_id`.