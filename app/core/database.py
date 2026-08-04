"""
SQLAlchemy async sessions for API and Celery.

FastAPI uses pooled AsyncSessionLocal; Celery uses NullPool (prefork + asyncio.run
per task). All tenant data flows through these sessions into Supabase Postgres.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db_connect import async_connect_args

_connect_args = async_connect_args(settings.database_url)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args,
    pool_pre_ping=True,     # <--- Add this to health-check connections
    pool_recycle=300,
    pool_size=20,           # <--- Increase from default 5 to handle concurrent dashboard requests
    max_overflow=10,        # <--- Allow burst capacity without exhausting connections
    pool_timeout=30,        # <--- Wait up to 30s for a connection before failing
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Celery prefork workers: avoid pooled asyncpg connections across asyncio.run() calls.
celery_engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args,
)
CeleryAsyncSessionLocal = async_sessionmaker(
    celery_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
