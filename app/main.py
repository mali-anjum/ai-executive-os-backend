"""
FastAPI app entry — mounts v1 routers and CORS.

Two product flows share this process: Knowledge (ingest → query) and Tasks
(webhook → tickets). Background work is always delegated to Celery workers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import (
    analytics,
    connectors,
    demo,
    evaluation,
    health,
    ingest,
    profile,
    query,
    settings as settings_router,
    tickets,
    webhooks,
)
from app.core.feature_registry import get_public_config
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers

API_DESCRIPTION = """
## SOP Automator API

Knowledge Agent (RAG), document ingestion, multi-tenant org isolation, and admin analytics.

### Authentication
Send `Authorization: Bearer <supabase_jwt>` with `user_metadata.org_id` and `user_metadata.role`.

For local dev (`APP_ENV=development`), you may use headers: `X-Org-Id`, `X-User-Id`, `X-User-Role` (`admin` | `employee`). Production requires a verified Supabase JWT (`SUPABASE_URL` + JWKS).

### Sprint 2 endpoints
- `POST /api/v1/query/stream` — SSE token streaming with citations on `done` event
- `GET /api/v1/analytics/dashboard` — admin metrics (requires admin role)
- `DELETE /api/v1/documents/{id}` — cascade delete chunks/embeddings

### Sprint 3 — Project Agent
- `POST /api/v1/webhook/slack` — Slack Events API (url_verification + message.channels)
- `GET /api/v1/tickets` — Ticket feed (org-scoped)
"""


# Optional startup/shutdown hook (uvicorn logs start/stop either way).
# Add code before/after yield for prod checks, Sentry, or closing DB/Redis pools.
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SOP Automator API",
    version="3.0.0",
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(health.router, prefix=api_prefix, tags=["health"])
app.include_router(profile.router, prefix=api_prefix, tags=["profile"])
app.include_router(ingest.router, prefix=api_prefix, tags=["documents"])
app.include_router(query.router, prefix=api_prefix, tags=["knowledge"])
app.include_router(analytics.router, prefix=api_prefix, tags=["analytics"])
app.include_router(webhooks.router, prefix=api_prefix, tags=["webhooks"])
app.include_router(tickets.router, prefix=api_prefix, tags=["tickets"])
app.include_router(evaluation.router, prefix=api_prefix, tags=["evaluation"])
app.include_router(connectors.router, prefix=api_prefix, tags=["connectors"])
app.include_router(settings_router.router, prefix=api_prefix, tags=["settings"])
app.include_router(demo.router, prefix=api_prefix, tags=["demo"])


@app.get(f"{api_prefix}/config/features")
async def public_features_config():
    return get_public_config()
