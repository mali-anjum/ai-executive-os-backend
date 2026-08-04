#!/usr/bin/env bash
# Apply Supabase SQL migrations to the database in ENV_FILE (default: .env.dev).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-.env.dev}"
ENV_PATH="$ROOT/$ENV_FILE"

if [[ ! -f "$ENV_PATH" ]]; then
  echo "Missing env file: $ENV_PATH" >&2
  exit 1
fi

if ! command -v supabase >/dev/null 2>&1; then
  echo "Supabase CLI not found. Install: https://supabase.com/docs/guides/cli" >&2
  echo "  corepack enable && corepack prepare pnpm@latest --activate" >&2
  echo "  pnpm add -g supabase   OR   npx supabase --version" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set in $ENV_FILE" >&2
  exit 1
fi

DB_URL="${DATABASE_URL/postgresql+asyncpg/postgresql}"

# Supabase pooler: port 6543 = transaction mode (no DDL). Migrations need session mode on 5432.
if [[ "$DB_URL" == *".pooler.supabase.com:6543"* ]]; then
  DB_URL="${DB_URL/:6543/:5432}"
  echo "Note: switched pooler port 6543 → 5432 (session mode required for migrations)" >&2
fi

MASKED_URL="$(echo "$DB_URL" | sed -E 's#(://[^:]+:)[^@]+#\1***#')"
echo "Applying Supabase migrations → $MASKED_URL"

cd "$ROOT"
supabase db push --db-url "$DB_URL" --yes
