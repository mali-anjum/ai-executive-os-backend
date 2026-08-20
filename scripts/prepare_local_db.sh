#!/usr/bin/env bash
# Create minimal Supabase Auth stubs on the LOCAL Docker Postgres so the
# Supabase-native migrations (0007+) can apply.
#
# Production already has the real `auth` schema and must never run this script.
# db_push.sh only calls it for 127.0.0.1 / localhost connection strings.
set -euo pipefail

DB_URL="${1:?usage: prepare_local_db.sh <postgresql://...>}"

psql "${DB_URL}" -v ON_ERROR_STOP=1 -q <<'SQL'
-- Minimal Supabase Auth compatibility for local Docker Postgres.
CREATE SCHEMA IF NOT EXISTS auth;

-- `authenticated` role is required by RLS policies (TO authenticated).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated;
    END IF;
END
$$;

-- auth.jwt(): returns JWT claims as jsonb. Local dev has no real JWT,
-- so a null/empty claims object is sufficient for DDL + function bodies.
CREATE OR REPLACE FUNCTION auth.jwt()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$ SELECT '{}'::jsonb $$;

-- auth.uid(): returns the current auth user id (null locally).
CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$ SELECT NULL::uuid $$;

-- auth.users: the table the signup trigger in migration 0010 targets.
CREATE TABLE IF NOT EXISTS auth.users (
    id                   uuid PRIMARY KEY,
    email                text,
    raw_user_meta_data   jsonb DEFAULT '{}'::jsonb,
    created_at           timestamptz DEFAULT now()
);
SQL

echo "Local Supabase Auth stubs ready."
