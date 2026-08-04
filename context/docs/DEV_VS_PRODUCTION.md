# Development vs production — complete guide

How to run **development** daily, how to **verify production settings** on your laptop before deploy, and what to change in `.env` / `.env.production`.

**Quick links**

| Topic | Jump to |
|-------|---------|
| Side-by-side comparison | [Dev vs production at a glance](#dev-vs-production-at-a-glance) |
| Check development is OK | [Verify development environment](#verify-development-environment) |
| Test production on laptop | [Test production locally](#test-production-on-your-laptop) |
| Switch env files safely | [Switching env files](#switching-env-files-safely) |
| Production on real server | [Real production deploy](#real-production-deploy) |
| Checklist PDF-style | [Master checklist](#master-checklist) |

Related: [ENV_QUICK_START.md](./ENV_QUICK_START.md) · [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) · [../README.md](../README.md)

---

## Don't confuse: `ENV_FILE` vs `APP_ENV` (backend)

| | **Which file loads** | **`APP_ENV` in that file** |
|--|----------------------|----------------------------|
| **Controlled by** | `pnpm run dev` → `.env.dev`; `pnpm run prod` → `.env.production` (`ENV_FILE` in pnpm scripts) | Variable inside the loaded file |
| **Does** | Picks `DATABASE_URL`, Redis, keys, etc. | Picks auth strictness and validation (not the file path) |

**`APP_ENV=production` inside `.env.dev` does not load `.env.production`.** Use `pnpm run prod` with `backend/.env.production` filled in.

Full explanation: [../README.md#dont-confuse-which-env-file-loads-vs-app_env-backend](../README.md#dont-confuse-which-env-file-loads-vs-app_env-backend) · [../backend/README.md](../backend/README.md#dont-confuse-env_file-vs-app_env)

---

## Dev vs production at a glance

| | **Development** | **Production** |
|---|-----------------|----------------|
| **Purpose** | Daily coding, hot reload | Same behavior as deployed server |
| **Backend active file** | `backend/.env.dev` (`pnpm run dev`) | `backend/.env.production` (`pnpm run prod`) |
| **Backend template** | `backend/.env.example` | copy to `.env.production` from example |
| **Frontend active file** | `frontend/.env.dev` | `frontend/.env.production` |
| **Frontend template** | `frontend/.env.example` | `frontend/.env.production.example` |
| **`APP_ENV`** | `development` | `production` or `prod` |
| **API auth** | Supabase JWT **or** dev headers `X-Org-Id`, `X-User-Id`, `X-User-Role` | **Supabase JWT only** |
| **Startup validation** | Warns on missing LLM key | **Exits** if `ENCRYPTION_KEY`, LLM key, etc. missing |
| **Backend start** | `pnpm run dev` (reload + Celery) | Server: `uvicorn` + `celery` (or Docker) |
| **Frontend start** | `pnpm run dev` | `pnpm run build` → `pnpm run start` |
| **Database (laptop)** | Docker `127.0.0.1:5433` recommended | Local `5433` OK for test; real deploy uses hosted Postgres |
| **Redis (laptop)** | `127.0.0.1:6379` or Docker `6380` | Local or Upstash `rediss://...` |

---

## Which file to edit

```text
ai-executive-os/
├── backend/
│   ├── .env                      ← ACTIVE for local runs (gitignored)
│   ├── .env.example              ← Dev template (commit)
│   ├── .env.production.example   ← Prod template (commit)
│   └── .env.production           ← Your prod secrets (gitignored) — create yourself
├── frontend/
│   ├── .env.local                ← ACTIVE for pnpm run dev (gitignored)
│   ├── .env.example              ← Dev template
│   └── .env.production             ← ACTIVE for pnpm run build (gitignored)
└── docker/
    └── .env                      ← Full stack Docker only
```

**Rule:** Never commit `.env`, `.env.local`, or `.env.production` with real secrets.

---

## Verify development environment

Use this **every day** or when something breaks after pulling code.

### 1. Backend config load + services

```bash
cd backend
pnpm run db:check
```

**Expect:**

```text
Checking Postgres… 127.0.0.1:5433/sop_automator
Checking Redis… redis://127.0.0.1:6379/0
Postgres and Redis OK.
```

### 2. Backend env validation (development rules)

```bash
cd backend
pnpm run check:env
```

**Expect:** `APP_ENV=development` and `Validation passed`.

### 3. Start backend

```bash
cd backend
pnpm run deps:docker    # if Postgres container not running
pnpm run dev
```

**Expect in terminal:**

- `[api] Uvicorn running on http://127.0.0.1:8000`
- `[worker] celery@... ready.`

### 4. Backend HTTP checks (new terminal)

```bash
curl -s http://127.0.0.1:8000/api/v1/health
# expect JSON with healthy status

curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/docs
# expect 200
```

### 5. Frontend

```bash
cd frontend
pnpm run dev
```

Open http://localhost:3000 — login page loads (Supabase configured).

### 6. End-to-end (manual)

1. Sign in with Supabase.
2. Open chat → send a message → streaming reply (or clear error if no docs).
3. Optional: upload a document → wait for Celery ingest → ask a question about it.

### Development `backend/.env` must include

| Variable | Example |
|----------|---------|
| `APP_ENV` | `development` |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `ENCRYPTION_KEY` | Fernet key |
| `SUPABASE_URL` | `https://<project>.supabase.co` |
| `GEMINI_API_KEY` | If `ai_provider` is `gemini` |

---

## Test production on your laptop

Goal: run with **`APP_ENV=production`** and production-like secrets **without** breaking your daily dev `.env`.

### Step 0 — Backup working dev env

```bash
cd backend
cp .env .env.development.backup

cd ../frontend
cp .env.local .env.development.backup
```

### Step 1 — Create production env files (first time)

```bash
cd backend
cp .env.production.example .env.production
# Edit .env.production: real keys, APP_ENV=production

cd ../frontend
cp .env.production.example .env.production
# Edit: same Supabase project, NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

For **local prod test**, you may keep the same `DATABASE_URL` as dev (Docker on `5433`) so you do not depend on Supabase network from your laptop. Use hosted `DATABASE_URL` only when testing remote DB on purpose.

**Remote Supabase from laptop:** see **[SUPABASE_REMOTE_DATABASE.md](./SUPABASE_REMOTE_DATABASE.md)** (pooler URI + `pnpm run dev:prod`).

**Recommended on laptop when remote DB fails (IPv6 / firewall):**

```bash
cd backend
cp .env.production.local.example .env.production.local
# Edit .env.production.local: paste SUPABASE_*, ENCRYPTION_KEY, GEMINI_* from .env.production
pnpm run deps:docker:all
pnpm run dev:prod:local
```

This runs `APP_ENV=production` (real JWT rules) against **local** Postgres on `5433` and Redis on `6380`.

| File | When |
|------|------|
| `.env.production` | Real deploy / remote Supabase + Upstash |
| `.env.production.local` | Laptop prod simulation (local DB) |

### Step 2 — Activate production backend env

**Option A — temporary copy (simple)**

```bash
cd backend
cp .env.production .env
pnpm run check:prod
pnpm run deps:docker
pnpm run dev
```

**Option B — keep dev file, override one variable (quick test)**

```bash
cd backend
APP_ENV=production pnpm run check:prod
# Fix any errors in .env, then:
APP_ENV=production pnpm run dev
```

`check:prod` validates **production rules** against values currently in `backend/.env`.

### Step 3 — Production backend checks

```bash
cd backend
pnpm run check:prod
```

**Must pass** before you trust prod mode:

| Check | Meaning |
|-------|---------|
| `ENCRYPTION_KEY` set | Required in production |
| `GEMINI_API_KEY` (or active provider) | Required for `ai_provider` in `features.json` |
| `DATABASE_URL` / `REDIS_URL` set | Required |
| `SUPABASE_URL` | Needed for real login (JWT verify) |

```bash
pnpm run db:check
curl -s http://127.0.0.1:8000/api/v1/health
```

### Step 4 — Frontend production-like

**Light test (same UI, prod backend):**

Keep `frontend/.env.local` and use `pnpm run dev` — enough to test JWT + chat against `APP_ENV=production` API.

**Full production frontend build:**

```bash
cd frontend
cp .env.production .env.production.local   # or ensure .env.production exists
pnpm run build
pnpm run start
```

Open http://localhost:3000 — this is optimized production Next.js, not hot reload.

### Step 5 — Production behavior to verify manually

| Test | Expected in production |
|------|------------------------|
| Open app without login | Redirect / login required for protected routes |
| Chat without token | **401** (dev headers do not work) |
| Chat after Supabase login | Works |
| Upload document | 202 + Celery processes (worker must run) |
| Wrong `SUPABASE_URL` on backend | 401 invalid token |

### Step 6 — Restore development

```bash
cd backend
cp .env.development.backup .env

cd ../frontend
cp .env.development.backup .env.local
```

---

## Switching env files safely

| Action | Command |
|--------|---------|
| Save dev backend | `cp backend/.env backend/.env.development.backup` |
| Use prod backend | `cp backend/.env.production backend/.env` |
| Restore dev backend | `cp backend/.env.development.backup backend/.env` |
| Save dev frontend | `cp frontend/.env.local frontend/.env.development.backup` |
| Use prod frontend build | `cp frontend/.env.production frontend/.env.production` + `pnpm run build` |

**Do not** delete `.env.development.backup` until prod test passed.

---

## What changes in the app when `APP_ENV=production`

| Feature | Development | Production |
|---------|-------------|------------|
| `X-Org-Id` / `X-User-Id` headers | Accepted (no JWT) | **Ignored** — JWT required |
| Startup missing `ENCRYPTION_KEY` | May warn | **Process exits** |
| Missing LLM API key | May fail at query time | **Startup validation error** |
| CORS | `http://localhost:3000` | Your real frontend domain in `CORS_ORIGINS` |
| Encryption default | Dev fallback string | Must use real `ENCRYPTION_KEY` |

Code references: `backend/app/core/security.py`, `backend/app/core/startup.py`.

---

## Real production deploy

| Component | Typical setup |
|-----------|----------------|
| Backend | `APP_ENV=production`, hosted Postgres + Redis, secrets on host |
| Frontend | Vercel/host with `NEXT_PUBLIC_*` env vars |
| Migrations | `alembic upgrade head` before or during deploy |
| Processes | `uvicorn` + `celery worker` (or Docker `api` + `worker` services) |

Use `backend/.env.production` as a **reference** when setting server secrets — do not commit it.

---

## Master checklist

### Development OK?

- [ ] `cd backend && pnpm run db:check` → Postgres and Redis OK
- [ ] `cd backend && pnpm run check:env` → Validation passed
- [ ] `cd backend && pnpm run dev` → API + Celery ready
- [ ] `curl http://127.0.0.1:8000/api/v1/health` → OK
- [ ] `cd frontend && pnpm run dev` → http://localhost:3000 loads
- [ ] Login + chat works

### Production-ready (local simulation)?

- [ ] `backend/.env.production.local` created from `.env.production.local.example` + secrets from `.env.production`
- [ ] `APP_ENV=production`
- [ ] `cd backend && ENV_FILE=.env.production.local pnpm run check:prod` → Validation passed
- [ ] `pnpm run db:check:prod:local` → OK (Docker Postgres + Redis)
- [ ] `pnpm run dev:prod:local` → starts without exit
- [ ] Chat works **only when logged in** (no dev headers)
- [ ] Optional: `cd frontend && pnpm run build && pnpm run start` → prod UI
- [ ] Restored `.env.development.backup` → dev workflow again

---

## One-command start

From **repo root** (starts backend + frontend):

| Command | Env files | What runs |
|---------|-----------|-----------|
| `pnpm run dev` | `backend/.env.dev` + `frontend/.env.dev` | Docker Postgres/Redis → check → migrate → API + Celery + Next dev |
| `pnpm run prod` | `backend/.env.production` + `frontend/.env.production` | Verify Supabase refs → check → migrate remote DB → API + Celery + Next dev |

Per package only:

```bash
cd backend && pnpm run dev    # .env.dev
cd backend && pnpm run prod   # .env.production

cd frontend && pnpm run dev   # .env.dev
cd frontend && pnpm run prod  # .env.production
```

First time: `pnpm run setup` from repo root.

---

## pnpm scripts reference

### Backend (`backend/package.json`)

| Script | When |
|--------|------|
| `pnpm run check:env` | Validate **development** rules |
| `pnpm run check:prod` | Validate **production** rules (current `.env` values) |
| `pnpm run db:check` | TCP check Postgres + Redis |
| `pnpm run dev` | Run API + worker (dev or prod `APP_ENV`) |

### Frontend (`frontend/package.json`)

| Script | When |
|--------|------|
| `pnpm run dev` | Development UI |
| `pnpm run build` | Production build |
| `pnpm run start` | Serve production build |

---

## Troubleshooting production test

| Problem | Fix |
|---------|-----|
| `check:prod` fails on LLM key | Set `GEMINI_API_KEY` (or provider in `features.json`) |
| `check:prod` fails on `ENCRYPTION_KEY` | Generate Fernet key (see README) |
| Chat 401 in prod mode | Log in via Supabase; align `SUPABASE_URL` backend = frontend project |
| Startup exit code 1 | Read log lines from `startup_validation` |
| Still uses dev headers | Set `APP_ENV=production` and restart `pnpm run dev` |