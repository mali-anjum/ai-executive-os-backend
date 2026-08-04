# 9. Environment Variables Reference

Engineering master guide §9, aligned with **`backend/app/core/config.py`**.

**Setup:** copy [`docker/.env.example`](../docker/.env.example) → `docker/.env` and [`frontend/.env.example`](../frontend/.env.example) → `frontend/.env.local`.

---

## Master reference table

| Variable | Required | Description | Where to get it | In this repo |
|----------|----------|-------------|-----------------|--------------|
| `OPENAI_API_KEY` | **Yes** | OpenAI API access for GPT-4o + embeddings | [platform.openai.com](https://platform.openai.com) | Same |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string | Local: `docker-compose`. Prod: Supabase / Railway / Neon | `postgresql+asyncpg://...` |
| `REDIS_URL` | **Yes** | Redis for Celery + RAG cache | Local: `docker-compose`. Prod: Upstash / Railway | Same |
| `SUPABASE_URL` | **Yes**† | Supabase project URL | [supabase.com](https://supabase.com) dashboard | Backend storage; use `NEXT_PUBLIC_SUPABASE_URL` in frontend |
| `SUPABASE_SERVICE_KEY` | — | *(PDF name)* | — | Use **`SUPABASE_SERVICE_ROLE_KEY`** instead |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes**† | Supabase admin key for storage | Dashboard → Settings → API → `service_role` | Optional; else local `UPLOAD_DIR` |
| `NEXTAUTH_SECRET` | — | *(PDF)* NextAuth JWT signing | — | Supabase Auth JWTs verified via **`SUPABASE_URL`** (JWKS) |
| `NEXTAUTH_URL` | — | *(PDF)* Next.js base URL | — | Use app URL + **`NEXT_PUBLIC_SUPABASE_URL`** |
| `NEXT_PUBLIC_SUPABASE_URL` | **Yes** | Supabase URL (browser) | Supabase dashboard | Frontend auth |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Yes** | Supabase anon key | Supabase dashboard | Frontend auth |
| `SUPABASE_JWT_SECRET` | — | *(deprecated)* Legacy HS256 verify only | Supabase → JWT Settings → Legacy JWT secret | Omit if using asymmetric signing keys |
| `NEXT_PUBLIC_API_URL` | **Yes** | API base for frontend | e.g. `http://localhost:8000/api/v1` | Frontend |
| `SLACK_BOT_TOKEN` | Sprint 3 | Slack bot OAuth for DMs | [api.slack.com](https://api.slack.com) → App credentials | Same |
| `SLACK_SIGNING_SECRET` | Sprint 3 | Slack webhook HMAC | Same | Same |
| `DEFAULT_ORG_ID` | Sprint 3 | Org UUID for Slack/email webhooks | `user_metadata.org_id` in Supabase | Same |
| `JIRA_BASE_URL` | Sprint 4 | Jira instance URL | `yourcompany.atlassian.net` | **Admin → Settings UI** (encrypted DB), not env |
| `JIRA_API_TOKEN` | Sprint 4 | Jira API token | [id.atlassian.com](https://id.atlassian.com) → API tokens | **Settings UI** → OAuth access token |
| `JIRA_EMAIL` | Sprint 4 | Jira API user email | Your Atlassian account | Not required (OAuth bearer) |
| `SENDGRID_API_KEY` | Sprint 4 | SendGrid inbound + outbound email | [app.sendgrid.com](https://app.sendgrid.com) | **Settings UI** (encrypted DB) |
| `COHERE_API_KEY` | Sprint 2 | Cohere Rerank API | [cohere.com](https://cohere.com) | Same |
| `ENCRYPTION_KEY` | Sprint 4 | Fernet key for stored API secrets | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Same |
| `SENTRY_DSN` | Sprint 5 | Sentry DSN (backend) | [sentry.io](https://sentry.io) | Same |
| `NEXT_PUBLIC_SENTRY_DSN` | Sprint 5 | Sentry DSN (browser) | Sentry → Frontend project | Frontend |
| `FEATURE_PROJECT_AGENT_ENABLED` | Sprint 3 | Override project agent flag | `true` / `false` | Same (+ other `FEATURE_*` below) |

† **Supabase storage:** required only if not using local `UPLOAD_DIR`. Auth vars are always required for the frontend.

---

## Additional variables (implemented, not in PDF table)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_GRADING_MODEL` | No | Default `gpt-4o-mini` for chunk grading |
| `LLM_PROVIDER` | No | `groq` \| `gemini` \| `openai` \| `anthropic` — see `backend/config/llm_providers.json` |
| `FEATURE_CUSTOM_LLM_PROVIDER_ENABLED` | No | `false` forces OpenAI; `true` uses `LLM_PROVIDER` |
| `GROQ_API_KEY` | If Groq | [console.groq.com](https://console.groq.com) — free tier |
| `GEMINI_API_KEY` | If Gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GROQ_CHAT_MODEL` / `GROQ_GRADING_MODEL` | No | Defaults in registry JSON |
| `GEMINI_CHAT_MODEL` / `GEMINI_GRADING_MODEL` | No | Defaults in registry JSON |
| `ANTHROPIC_API_KEY` | If Anthropic | Claude when `LLM_PROVIDER=anthropic` |
| `APP_ENV` | Prod | `production` runs startup validation |
| `CORS_ORIGINS` | Prod | Comma-separated allowed origins |
| `EMBEDDING_BATCH_SIZE` | No | Default `100` for ingest |
| `RAG_CACHE_TTL_SECONDS` | No | Default `3600` |
| `SUPABASE_STORAGE_BUCKET` | No | Default `documents` |
| `UPLOAD_DIR` | No | Local file path when Supabase storage off |

---

## Feature flags (`FEATURE_*` prefix)

| Variable | Sprint | Default |
|----------|--------|---------|
| `FEATURE_KNOWLEDGE_AGENT_ENABLED` | 1–2 | `true` |
| `FEATURE_DOCUMENT_UPLOAD_ENABLED` | 1–2 | `true` |
| `FEATURE_MULTI_TENANT_ENABLED` | 2 | `true` |
| `FEATURE_ANALYTICS_DASHBOARD_ENABLED` | 2 / 5 | `true` |
| `FEATURE_PROJECT_AGENT_ENABLED` | 3 | `true` |
| `FEATURE_SLACK_WEBHOOK_ENABLED` | 3 | `true` |
| `FEATURE_JIRA_INTEGRATION_ENABLED` | 4 | `true` |
| `FEATURE_EMAIL_WEBHOOK_ENABLED` | 4 | `true` |
| `FEATURE_WORKLOAD_BALANCING_ENABLED` | 4 | `true` |
| `FEATURE_AUDIT_LOG_ENABLED` | 4 | `true` |
| `FEATURE_RAG_CACHE_ENABLED` | 5 | `true` |
| `FEATURE_CUSTOM_LLM_PROVIDER_ENABLED` | 5 | `true` |

Frontend mirror: `frontend/src/config/features.config.ts`.

---

## Sprint 4 integrations (Settings UI, not `.env`)

Configure in the app as **admin** → **Settings** (`PUT /api/v1/settings/integrations`). Values are Fernet-encrypted in `org_integration_settings`:

| Setting field | Replaces PDF env |
|---------------|------------------|
| `jira_site_url` | `JIRA_BASE_URL` |
| `jira_access_token` | `JIRA_API_TOKEN` |
| `jira_project_key` | — |
| `sendgrid_api_key` | `SENDGRID_API_KEY` |
| `sendgrid_from_email` | — |
| `inbound_email_address` | — |

Requires `ENCRYPTION_KEY` on the API.

---

## PDF → repo name mapping (quick)

| Engineering PDF | Use in this repo |
|-----------------|------------------|
| `SUPABASE_SERVICE_KEY` | `SUPABASE_SERVICE_ROLE_KEY` |
| `NEXTAUTH_SECRET` | `SUPABASE_URL` (JWKS JWT verify) |
| `NEXTAUTH_URL` | `NEXT_PUBLIC_SUPABASE_URL` + deployment URL |
| `JIRA_*` / `SENDGRID_API_KEY` | Admin **Settings** UI |
