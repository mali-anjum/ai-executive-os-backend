# Backend code design patterns

**Mandatory reading for AI agents and contributors working in `backend/`.**  
Follow these patterns to avoid architectural drift. When in doubt, match existing files before inventing new abstractions.

Related: [`context/specs/01-supabase-native-migration.md`](specs/01-supabase-native-migration.md) · [`supabase/README.md`](../supabase/README.md)

---

## 1. Architecture layers (strict)

```text
HTTP request
    ↓
api/v1/routers/     ← thin: auth deps, validate input, call service, return schema
    ↓
services/           ← business logic, DB queries, external APIs
    ↓
models/db/tables    ← SQLAlchemy ORM (schema mirror of supabase/migrations/)
agents/             ← LangGraph pipelines (orchestrate services)
tasks/              ← Celery entrypoints (call services, never routers)
```

| Layer | May import | Must NOT import |
|-------|------------|-----------------|
| **Routers** | `services`, `core`, `models/http` | Other routers, `agents` directly (prefer service) |
| **Services** | `models/db`, `core`, other services | FastAPI, routers |
| **Agents** | `services`, `core`, `prompts` | Routers, FastAPI |
| **Tasks** | `services`, `core`, `tasks/celery_app` | Routers |
| **Core** | stdlib, third-party only | `services`, `routers`, `agents` |

**Rule:** Routers stay thin (~10–40 lines per handler). If logic exceeds that, move it to a service.

---

## 2. Database & migrations

| Rule | Detail |
|------|--------|
| **Single source of truth** | `supabase/migrations/*.sql` only |
| **Never use Alembic** | Decommissioned — do not recreate `backend/alembic/` |
| **Never dashboard-edit** | No schema changes in Supabase UI without a migration file |
| **ORM mirror** | `app/models/db/tables.py` reflects migration SQL; update both together |
| **New table checklist** | DDL migration + RLS policies + FK indexes + SQLAlchemy model |
| **Apply locally** | `cd backend && pnpm run db:migrate` |
| **Apply production** | `cd backend && pnpm run db:migrate:prod` |
| **New migration** | `supabase migration new <name>` → SQL → `supabase db push` |

---

## 3. Configuration

- **Only** `app/core/config.py` reads environment variables (`Settings` + `ENV_FILE`).
- Never `os.environ` elsewhere — use `from app.core.config import settings`.
- Dev: `backend/.env.dev` via `pnpm run dev`. Prod: `backend/.env.production` via `pnpm run prod`.
- `APP_ENV=development` enables dev auth headers; production requires Supabase JWT only.

---

## 4. Authentication & authorization

```python
# Standard protected route
async def handler(
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID = Depends(tenant_org_id),
    db: AsyncSession = Depends(get_db),
): ...

# Admin-only
async def handler(auth: AuthContext = Depends(require_admin), ...): ...
```

| Concern | Location |
|---------|----------|
| JWT decode | `app/core/supabase_jwt.py` |
| Auth deps | `app/core/security.py` |
| User/org row sync | `app/core/tenant_sync.py` |
| Role enum coercion | `app/models/internal/coerce.py` |

**Never** put RBAC or auth checks in agents, tasks, or LLM circuit breakers.

---

## 5. Feature flags

- Read flags via `from app.core.feature_flags import flags`.
- Register new flags in `config/features.json` + `app/core/feature_registry.py`.
- Gate routes with early `HTTPException(404)` when disabled — do not half-implement.

---

## 6. HTTP models

| Type | Location | Naming |
|------|----------|--------|
| Request/response bodies | `app/models/http/schemas.py` | `*Request`, `*Response` |
| Enums | `app/models/http/enums.py` | `StrEnum` or string literals |
| OpenAPI errors | `app/models/http/responses.py` | `STANDARD_ERROR_RESPONSES` |
| SSE events | `app/models/http/stream.py` | `Stream*Event` |

Use Pydantic models at router boundaries; pass plain types or ORM objects inside services.

---

## 7. Services

- One service class or module per domain: `DocumentService`, `TicketService`, etc.
- Methods take `AsyncSession` as first arg after `self`: `async def foo(self, db: AsyncSession, ...)`.
- Services raise domain exceptions or return `None`; routers translate to HTTP status codes.
- No raw SQL strings unless performance-critical — prefer SQLAlchemy 2.0 `select()` / `update()`.

---

## 8. Agents (LangGraph)

- Agents live in `app/agents/` — explicit `StateGraph`, not open ReAct loops.
- Prompts in `app/prompts/` — no inline 50-line strings in agent files.
- Agents call services for DB/vector/LLM; they do not import routers.
- Failed nodes → explicit error handler node; never silent `except: pass`.

---

## 9. Background tasks (Celery)

```python
@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> str:
    async def _process():
        async with CeleryAsyncSessionLocal() as db:
            await DocumentService().process_document(db, uuid.UUID(document_id))
    asyncio.run(_process())
    return document_id
```

- Tasks in `app/tasks/` — thin bridges that call services.
- Use `CeleryAsyncSessionLocal` (not `AsyncSessionLocal`) in workers.
- Queue from routers via `.delay()`: `process_document.delay(str(doc.id))`.

---

## 10. Error handling

- Register handlers in `app/core/exception_handlers.py`.
- Routers: `HTTPException` for client errors; log + 500 for unexpected failures.
- External API failures (Slack, Jira, LLM): catch in service, return structured fallback.

---

## 11. Naming & files

| Item | Convention |
|------|------------|
| Routers | `app/api/v1/routers/<domain>.py`, `router = APIRouter()` |
| Services | `app/services/<domain>_service.py`, class `<Domain>Service` |
| Tests | `backend/tests/unit/test_<module>.py` |
| Scripts | `backend/scripts/<verb>_<noun>.py` |
| Module docstring | First line = one-sentence purpose |

---

## 12. Testing

- Unit tests in `tests/unit/` — mock DB, Redis, LLM, external HTTP.
- Use `pytest` + `pytest-asyncio` (`asyncio_mode = auto`).
- Patch at **import site** (where symbol is used), not definition site.
- No live network in unit tests.

---

## 13. What NOT to do (drift guards)

| Anti-pattern | Do instead |
|--------------|------------|
| New Alembic revision | `supabase migration new` |
| Schema change in dashboard | SQL migration file |
| Business logic in router | Service method |
| `os.getenv` in random files | `settings` from config |
| Auth in `knowledge_agent.py` | `security.py` deps |
| Direct SQLAlchemy in router | Service |
| New global singletons | Inject via deps or service `__init__` |
| Duplicate HTTP schemas | Extend `schemas.py` |

---

## 14. Adding a new feature (checklist)

1. Spec or issue in `context/specs/` if non-trivial.
2. SQL migration in `supabase/migrations/` (+ RLS if new table).
3. Update `tables.py` if schema changed.
4. Service method(s).
5. Router endpoint(s) with auth + feature flag.
6. Pydantic schemas.
7. Unit tests.
8. Update `context/progress.md`.

---

## 15. Key file map

| Area | Path |
|------|------|
| App entry | `app/main.py` |
| Settings | `app/core/config.py` |
| DB session | `app/core/database.py` |
| ORM models | `app/models/db/tables.py` |
| Migrations | `supabase/migrations/` |
| Knowledge RAG | `app/agents/knowledge_agent.py` |
| Ticket routing | `app/agents/project_agent.py` |
| Celery app | `app/tasks/celery_app.py` |
