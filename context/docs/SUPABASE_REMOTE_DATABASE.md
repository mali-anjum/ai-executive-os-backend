# Remote Supabase Postgres from your laptop

Use this when you want **`backend/.env.production`** (or `.env` copied from it) to hit **hosted** Postgres, not Docker on `5433`.

---

## 1. Get the correct connection string

In [Supabase Dashboard](https://supabase.com/dashboard) → your project → **Connect** (or **Project Settings → Database**):

1. Choose **ORM** / **URI**.
2. Prefer **Session pooler** (recommended for apps + laptops):
   - Host looks like: `aws-0-<region>.pooler.supabase.com`
   - Port **5432** (session) or **6543** (transaction)
   - User often: `postgres.<project-ref>` (not just `postgres`)
3. Copy the URI and convert to this repo’s format:

```env
DATABASE_URL=postgresql+asyncpg://postgres.PROJECT_REF:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
```

Replace `postgresql://` with `postgresql+asyncpg://` and URL-encode special characters in the password (`@`, `#`, `%`, etc.).

**Avoid** using the old direct host if your network breaks IPv6:

```text
db.<project-ref>.supabase.co:5432   ← often fails with "Network is unreachable"
```

---

## 2. Set `backend/.env.production`

```env
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://...pooler.supabase.com:5432/postgres
REDIS_URL=rediss://...   # Upstash or local redis://127.0.0.1:6380/0
CORS_ORIGINS=http://localhost:3000
SUPABASE_URL=https://<project-ref>.supabase.co
# ... ENCRYPTION_KEY, GEMINI_API_KEY, etc.
```

For local UI testing, **`CORS_ORIGINS` must include** `http://localhost:3000`.

---

## 3. Activate and verify

```bash
cd backend
cp .env.production .env          # optional: make .env the active file
pnpm run check:prod
pnpm run db:check:prod
pnpm run db:migrate:prod
pnpm run dev:prod
```

Or without overwriting `.env`:

```bash
pnpm run db:check:prod
pnpm run db:migrate:prod
pnpm run dev:prod
```

**Expect:** `Checking Postgres… … (using IPv4 x.x.x.x)` then `Postgres and Redis OK.`

---

## 4. Frontend

`frontend/.env.production`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

```bash
cd frontend
pnpm run dev:prod
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Network is unreachable` + IPv6 `2600:…` | Switch to **pooler** URI; repo forces IPv4 when possible |
| `could not translate host name` | Wrong host, offline DNS, or typo in `DATABASE_URL` |
| `password authentication failed` | Reset DB password in Supabase; update URI |
| `Tenant or user not found` | Use pooler user `postgres.<project-ref>`, not `postgres` alone |
| Project paused | Resume project in Supabase dashboard |

---

## IPv4 add-on (optional)

If you must use **direct** `db.*.supabase.co`, enable **IPv4 add-on** in Supabase (paid) and use the IPv4 connection string from the dashboard.
