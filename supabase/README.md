# Supabase database migrations

**Single source of truth** for schema changes. Alembic is decommissioned — do not add files under `backend/alembic/`.

## Quick commands

From repo root (requires [Supabase CLI](https://supabase.com/docs/guides/cli)):

```bash
# Apply migrations to local Docker Postgres (.env.dev)
cd backend && pnpm run db:migrate

# Apply to production / remote Supabase (.env.production)
cd backend && pnpm run db:migrate:prod

# List migration status
supabase migration list --db-url "postgresql://postgres:postgres@127.0.0.1:5433/sop_automator"

# Create a new migration (DDL only)
supabase migration new add_my_feature
# Edit supabase/migrations/<timestamp>_add_my_feature.sql
supabase db push --db-url "$DATABASE_URL"
```

## Local development

1. Start Postgres: `cd backend && pnpm run deps:docker`
2. Ensure `backend/.env.dev` uses local DB:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator
   ```
3. Apply migrations: `cd backend && pnpm run db:migrate`

Optional — full Supabase local stack (Auth, Studio, Storage):

```bash
supabase start    # uses ports in config.toml (54322 for DB)
supabase stop
```

## Remote Supabase

Use the **Session pooler** URI from the Supabase dashboard (not direct `db.*.supabase.co` on IPv6-only networks). See [`docs/SUPABASE_REMOTE_DATABASE.md`](../docs/SUPABASE_REMOTE_DATABASE.md).

```bash
cd backend && pnpm run db:migrate:prod
```

## Migrating from Alembic (existing database)

If your database was already migrated with Alembic and has all tables, **mark Supabase migrations as applied** without re-running DDL:

```bash
cd supabase
for v in 20260603000001 20260603000002 20260603000003 \
         20260603000004 20260603000005 20260603000006 20260603000007; do
  supabase migration repair "$v" --status applied --db-url "$DB_URL"
done
supabase migration list --db-url "$DB_URL"
```

Replace `$DB_URL` with your connection string (`postgresql://...`, not `+asyncpg`).

## Error: `relation "supabase_migrations.schema_migrations" does not exist`

This means the Supabase migration tracking schema was never initialized on that database. Running `supabase db push` creates it automatically and applies pending migrations.

For a **fresh empty database**, `supabase db push` applies all files in order.

For an **Alembic-managed database**, use `migration repair` (above) instead of re-applying DDL.

## Error: `Invalid db.major_version: 16`

Set `major_version = 15` in `supabase/config.toml`. The CLI (installed via pnpm/npm) may reject 16 even when your remote project runs Postgres 15.

## Error: migrations fail on pooler port 6543

`DATABASE_URL` with `:6543` is the **transaction** pooler — it cannot run DDL.  
Use session pooler **`:5432`** for migrations. `backend/scripts/db_push.sh` auto-converts `6543 → 5432`.

## Agent / contributor rules

1. **Never** edit schema in the Supabase Dashboard UI — always add a migration file.
2. **Never** add Alembic revisions.
3. Every new table: enable RLS + org-scoped policies (see `20260603000007_row_level_security.sql`).
4. Every foreign key: add an index on the referencing column.
5. When unsure of drift: `supabase db diff --db-url "$DB_URL"`.

See also: [`context/specs/01-supabase-native-migration.md`](../context/specs/01-supabase-native-migration.md)
