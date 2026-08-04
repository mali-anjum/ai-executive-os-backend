# Backend — AI Executive OS

FastAPI API for the AI Executive OS: Supabase JWT auth, multi-tenant Postgres (pgvector), RAG query/streaming, document ingest (Celery), analytics, tickets, and webhooks (Slack, etc.).

**Dev vs production env:** [`context/docs/DEV_VS_PRODUCTION.md`](context/docs/DEV_VS_PRODUCTION.md)  
**Remote Supabase DB:** [`context/docs/SUPABASE_REMOTE_DATABASE.md`](context/docs/SUPABASE_REMOTE_DATABASE.md)  
**Environment variables:** [`context/docs/ENVIRONMENT_VARIABLES.md`](context/docs/ENVIRONMENT_VARIABLES.md) · [`context/docs/ENV_QUICK_START.md`](context/docs/ENV_QUICK_START.md)  
**CI/CD:** [`context/docs/CI_CD.md`](context/docs/CI_CD.md)

---

## What this service does

| Capability | Entry | Notes |
|------------|--------|--------|
| **Health** | `GET /api/v1/health` | Liveness for deploys and local checks |
| **RAG chat** | `POST /api/v1/query`, `/query/stream` | LangGraph knowledge agent, citations, org isolation |
| **Ingest** | `POST /api/v1/ingest` | Queues Celery job: parse → chunk → embed → pgvector |
| **Documents** | `GET /api/v1/documents` | Tenant-scoped library |
| **Analytics** | `GET /api/v1/analytics` | Dashboard metrics (feature-flagged) |
| **Tickets** | `GET /api/v1/tickets` | Project agent output (feature-flagged) |
| **Auth context** | All protected routes | JWT → `AuthContext` → `tenant_sync` in Postgres |
| **Feature flags** | `GET /api/v1/config/features` | [`config/features.json`](config/features.json) |

Background work runs in **Celery** (Redis broker). Local dev starts Postgres (+ optional Redis) via **Docker Compose** in [`docker/docker-compose.yml`](docker/docker-compose.yml).

---

## Prerequisites

| Tool | Version | Used for |
|------|---------|----------|
| **Python** | 3.12+ (`python3`) | FastAPI, Alembic, Celery |
| **Node.js** | 18+ | `pnpm run` orchestration only (not the runtime) |
| **pnpm** | 11.17.0 | Package manager (via `corepack`) |
| **Docker** | recent | Local Postgres on host **5433**, Redis on **6380** when using `deps:docker:all` |
| **Redis** | optional | `6379` if already running locally; else Docker maps **6380** |

Accounts / keys:

- [Supabase](https://supabase.com) — auth JWT (JWKS); optional hosted Postgres in production
- LLM key for `ai_provider` in [`config/features.json`](config/features.json) (default: **gemini** → `GEMINI_API_KEY`)
- `ENCRYPTION_KEY` (Fernet) for encrypted settings

Generate encryption key once:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Environment files

Two active files — never commit secrets:

| File | Used by | Purpose |
|------|---------|---------|
| `.env.dev` | `pnpm run dev` | Local Docker Postgres `:5433`, local Redis, development rules |
| `.env.production` | `pnpm run prod` | Session pooler `DATABASE_URL`, Upstash `rediss://`, production validation |

### Don't confuse: `ENV_FILE` vs `APP_ENV`

These are **two separate knobs**. New contributors should read this before editing env files.

| | **`ENV_FILE` (which file)** | **`APP_ENV` (behavior inside the file)** |
|--|-----------------------------|------------------------------------------|
| **Set by** | `pnpm` scripts: `ENV_FILE=.env.dev` or `ENV_FILE=.env.production` | A variable **inside** that file: `APP_ENV=development` or `APP_ENV=production` |
| **Defined in code** | [`app/core/config.py`](app/core/config.py) — `os.getenv("ENV_FILE", ".env.dev")` | Same file — field `app_env` / `settings.is_development` |
| **Controls** | `DATABASE_URL`, `REDIS_URL`, `SUPABASE_URL`, API keys, etc. | Auth strictness, startup validation, LLM production checks |

**Common mistake:** changing only `APP_ENV=production` in `.env.dev` while running `pnpm run dev`.  
That still loads **`.env.dev`** (local Docker DB), but disables dev auth headers and enables production rules.  
**Correct prod-like test:** fill **`backend/.env.production`** and run **`pnpm run prod`**.

```bash
# Which file loads (backend)
pnpm run dev   # ENV_FILE=.env.dev
pnpm run prod  # ENV_FILE=.env.production

# Manual uvicorn — must set ENV_FILE yourself
ENV_FILE=.env.production .venv/bin/uvicorn app.main:app --reload
```

`main.py` lifespan does **not** choose env files; settings load once at import from `config.py`.

Copy once:

```bash
cp .env.example .env.dev
# Optional prod testing:
cp .env.example .env.production
# Or use backend/.env.production.example if present in your clone
```

### Default local Docker credentials

| Setting | Value |
|---------|--------|
| User / password | `postgres` / `postgres` |
| Database | `sop_automator` |
| Host port | **5433** (mapped from container) |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` or `redis://127.0.0.1:6380/0` after `deps:docker:all` |

### Minimum `.env.dev`

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator
REDIS_URL=redis://127.0.0.1:6379/0
CORS_ORIGINS=http://localhost:3000
ENCRYPTION_KEY=<fernet-key>
SUPABASE_URL=https://<project-ref>.supabase.co
GEMINI_API_KEY=<if ai_provider is gemini>
```

`SUPABASE_URL` must be the **project root** (`https://<ref>.supabase.co`), not `/rest/v1/`.

---

## First time only (new contributor)

From **repo root** (recommended):

```bash
git clone <repo-url> ai-executive-os
cd ai-executive-os

pnpm install
pnpm run setup

cp backend/.env.example backend/.env.dev
cp frontend/.env.example frontend/.env.dev
# Edit backend/.env.dev and frontend/.env.dev

cd backend && pnpm run bootstrap
```

`bootstrap` = Docker Postgres → Python `.venv` + pip → Alembic migrate on local DB.

**Backend-only** (this folder):

```bash
cd backend
cp .env.example .env.dev
# Edit .env.dev
pnpm run bootstrap
```

---

## Every day — local development

`pnpm run dev` is a **single chained command**: Docker (Postgres + Redis) → env validation → DB check → migrate → API (**hot reload**) + Celery worker in parallel.

### One command (recommended)

From **repo root** (backend + frontend):

```bash
pnpm run dev
```

### One command (this folder only)

```bash
cd backend
pnpm run dev
```

| URL | Service |
|-----|---------|
| http://127.0.0.1:8000 | API |
| http://127.0.0.1:8000/docs | OpenAPI (Swagger) |
| http://127.0.0.1:8000/api/v1/health | Health |

After reboot, if containers stopped:

```bash
pnpm run deps:docker:all
pnpm run dev
```

### Run API or worker alone

| Command | What it does |
|---------|----------------|
| `pnpm run api` | Uvicorn only (`.env.dev`, assumes DB ready) |
| `pnpm run worker` | Celery only |
| `pnpm run deps:docker` | Postgres container only |
| `pnpm run deps:docker:all` | Postgres + Redis |

`predev` (before `dev`) runs `db:check` + `db:migrate` automatically.

---

## Test production-like behavior (on your laptop)

Connects to **remote Supabase** (Session pooler) and runs production env checks before starting API + worker.

### One command (repo root)

```bash
pnpm run prod
```

### One command (this folder only)

```bash
cd backend
pnpm run prod
```

`preprod` runs: `verify:supabase` → `check:prod` → `db:check:prod` → `db:migrate:prod`.

Prepare `.env.production` first — see [`context/docs/SUPABASE_REMOTE_DATABASE.md`](context/docs/SUPABASE_REMOTE_DATABASE.md).

```bash
pnpm run verify:supabase
pnpm run check:prod
```

Alias: `pnpm run dev:prod` → same as `pnpm run prod`.

---

## How to verify it works

```bash
# After pnpm run dev
curl -s http://127.0.0.1:8000/api/v1/health

# Postgres (port must match DATABASE_URL)
PGPASSWORD=postgres psql -h 127.0.0.1 -p 5433 -U postgres -d sop_automator -c "SELECT 1;"

# Env validation
pnpm run check:env      # .env.dev
pnpm run check:prod     # .env.production
pnpm run db:check       # connectivity from .env.dev
```

Pair with frontend: [`../frontend/README.md`](../frontend/README.md) — the frontend lives in its own repository.

---

## pnpm scripts (full table)

| Command | What it does |
|---------|----------------|
| `pnpm run setup` | Create `.venv`, `pip install`, pnpm dev deps |
| `pnpm run bootstrap` | **First time:** Docker Postgres → setup → migrate |
| `pnpm run deps:docker` | Start Postgres (`:5433`) |
| `pnpm run deps:docker:all` | Postgres + Redis (`:6380` on host) |
| `pnpm run check:env` | Validate `.env.dev` |
| `pnpm run check:prod` | Validate `.env.production` |
| `pnpm run verify:supabase` | URL, DB user ref, JWT project ref alignment |
| `pnpm run db:check` | Test Postgres + Redis (dev) |
| `pnpm run db:migrate` | `supabase db push` via `scripts/db_push.sh` (dev) |
| `pnpm run db:check:prod` | Connectivity (production env) |
| `pnpm run db:migrate:prod` | Migrations against production DB |
| `pnpm run dev` | **Daily dev** — Docker + checks + API reload + Celery |
| `pnpm run prod` | **Daily prod test** — verify + remote DB + API + Celery |
| `pnpm run api` / `api:prod` | Uvicorn only |
| `pnpm run worker` / `worker:prod` | Celery only |

Scripts set `ENV_FILE=.env.dev` or `.env.production` and use `.venv/bin/` for Python tools.

### Manual (without pnpm)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && pnpm run db:migrate
ENV_FILE=.env.dev uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# second terminal:
ENV_FILE=.env.dev celery -A app.tasks.celery_app.celery_app worker --loglevel=info
```

---

## Project structure

```text
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, router mount
│   ├── api/v1/routers/         # HTTP: query, ingest, documents, tickets, analytics, health, webhooks
│   ├── agents/                 # LangGraph: knowledge_agent, project_agent
│   ├── core/                   # config, security, tenant_sync, db_connect, supabase_jwt, feature_flags
│   ├── models/                 # SQLAlchemy + Pydantic schemas
│   ├── services/               # RAG, embeddings, documents, LLM, tickets, analytics
│   └── tasks/                  # Celery app + document/slack tasks
├── supabase/migrations/        # DB migrations (Supabase CLI — single source of truth)
├── config/
│   └── features.json           # Feature flags + ai_provider
├── scripts/
│   ├── check_services.py       # DB + Redis preflight
│   ├── validate_env.py         # Env rules dev/prod
│   └── verify_supabase_env.py  # Cross-check Supabase refs
├── tests/
│   ├── unit/                   # Fast, no external services
│   └── integration/            # API + DB (need stack running)
├── .env.example
├── requirements.txt
└── package.json                # pnpm orchestration (not Python package name)
```

### Core files (start debugging here)

| File | Role |
|------|------|
| [`app/main.py`](app/main.py) | App entry, routers under `/api/v1` |
| [`app/core/security.py`](app/core/security.py) | JWT → `AuthContext` on each request |
| [`app/core/tenant_sync.py`](app/core/tenant_sync.py) | Sync JWT org/user into Postgres |
| [`app/core/config.py`](app/core/config.py) | Settings from `ENV_FILE` (`.env.dev` / `.env.production`) |
| [`app/core/db_connect.py`](app/core/db_connect.py) | SSL + IPv4 for Supabase; pooler hostname rules |
| [`app/core/supabase_jwt.py`](app/core/supabase_jwt.py) | JWKS verification (+ legacy HS256 fallback) |
| [`app/agents/knowledge_agent.py`](app/agents/knowledge_agent.py) | RAG / chat agent graph |

Map with frontend: [`context/docs/CORE_FILES.md`](context/docs/CORE_FILES.md)

### Data and tenancy

- **Postgres** — organizations, users, documents, chunks, vectors (`pgvector`), tickets, query logs
- **Supabase CLI** — schema changes in `supabase/migrations/` (see [`supabase/README.md`](supabase/README.md))
- **Multi-tenant** — JWT `org_id` / `user_id`; rows scoped per organization

---

## Feature flags and AI provider

Edit [`config/features.json`](config/features.json):

- Toggle UI/API features (`DOCUMENT_UPLOAD_ENABLED`, `ANALYTICS_DASHBOARD_ENABLED`, …)
- Set `"ai_provider": "gemini"` (or `groq`, `openai`, `anthropic`) and add the matching key in `.env`

Live values: `GET /api/v1/config/features`  
Details: [`context/docs/FEATURE_FLAGS.md`](context/docs/FEATURE_FLAGS.md)

Embeddings: prefer `OPENAI_API_KEY` for real vectors; without it, a dev hash fallback fills the 1536-dim schema.

---

## Static typing (Pyright)

The backend uses **Pyright** so API and domain types stay unambiguous at edit time and in OpenAPI.

| Layer | Location | Role |
|-------|----------|------|
| **ORM** | `app/models/db/tables.py` | SQLAlchemy tables |
| **HTTP enums** | `app/models/http/enums.py` | `Literal` types (`UserRole`, `DocumentStatus`, …) |
| **Request/response** | `app/models/http/schemas.py`, `errors.py` | Pydantic → OpenAPI + validation |
| **OpenAPI docs** | `app/models/http/responses.py` | Error shapes in `/docs` (not OpenAI) |
| **Domain (internal)** | `app/models/internal/domain.py` | `TypedDict` for RAG, citations |
| **Coercion** | `app/models/internal/coerce.py` | Narrow DB strings into `Literal` types |
| **Handlers** | `app/core/exception_handlers.py` | Every failure returns `ApiErrorResponse` |
| **SSE stream** | `app/models/http/stream.py` | Typed token/done/error events |

See [`app/models/README.md`](app/models/README.md) for the full folder map.

From **repo root** or **`backend/`**:

```bash
pnpm run typecheck              # root → backend Pyright
cd backend && pnpm run typecheck
```

Config: [`pyrightconfig.json`](pyrightconfig.json) (venv `.venv`, `typeCheckingMode: standard`).  
Dev dependency: `requirements-dev.txt` → `pyright`.

---

## Tests

```bash
cd backend
.venv/bin/python -m pytest tests/unit/ -q
.venv/bin/python -m pytest tests/integration/ -q   # needs API + DB + Redis running
```

---

## Dev vs production (backend)

Use the **file** (`pnpm run dev` / `prod`) for URLs and secrets; keep **`APP_ENV`** aligned with that file (usually `development` in `.env.dev`, `production` in `.env.production`).

| Variable | Development (`.env.dev`) | Production (`.env.production`) |
|----------|--------------------------|--------------------------------|
| `APP_ENV` | `development` | `production` |
| `DATABASE_URL` | `127.0.0.1:5433` (Docker) | Supabase Session pooler host |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Upstash `rediss://…` |
| Auth | Supabase JWKS + optional dev headers | JWT only (stricter) |

Switch modes by command, not by overwriting a single `.env` file.

---

## Related documentation

| Document | Purpose |
|----------|---------|
| [`context/docs/PROJECT_MASTER.md`](context/docs/PROJECT_MASTER.md) | Full engineering spec |
| [`context/docs/README.md`](context/docs/README.md) | Docs index |
| [`docker/docker-compose.yml`](docker/docker-compose.yml) | Postgres + Redis images and ports |

---

## Quick reference

| Goal | Command |
|------|---------|
| **First time** | `cp .env.example .env.dev` → edit → `pnpm run bootstrap` |
| **Daily dev** | `pnpm run dev` (Docker + migrate + API + worker) |
| **Daily prod test** | `pnpm run prod` (after `.env.production` is filled) |
| **Verify prod env** | `pnpm run verify:supabase && pnpm run check:prod` |
| **Migrations only** | `pnpm run db:migrate` or `pnpm run db:migrate:prod` |
| **Full stack from root** | `pnpm run dev` or `pnpm run prod` |