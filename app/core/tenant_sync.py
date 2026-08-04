"""
Multi-tenant bootstrap on first authenticated request.

Supabase Auth owns identity; this writes Organization + User rows in Postgres so
RAG, tickets, and analytics can FK by org_id. Called from get_current_user.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.models.db.tables import Organization, User

# In-memory cache of known (org_id, user_id) pairs to skip DB round-trips
# on every authenticated request. Safe because tenant_sync only needs to
# ensure rows exist once; after that, the rows are guaranteed present.
_known_orgs: set[str] = set()
_known_users: set[str] = set()


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (base[:120] or "org") + f"-{uuid.uuid4().hex[:6]}"


async def ensure_organization_row(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    org_name: str | None = None,
) -> None:
    name = (org_name or "Organization").strip() or "Organization"
    await db.execute(
        pg_insert(Organization)
        .values(
            id=org_id,
            name=name,
            slug=_slugify(name),
            plan="standard",
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org and org_name and org.name != org_name:
        org.name = org_name


async def ensure_user_row(
    db: AsyncSession,
    auth: AuthContext,
    metadata: dict | None = None,
) -> None:
    """Ensure org + user rows exist. Only commits when a write actually occurs.

    Previously this committed on every authenticated request (even read-only
    GETs), which added 2+ round-trips per request. Now we only commit when
    a new row is inserted or an existing row is updated.
    """
    org_key = str(auth.org_id)
    user_key = str(auth.user_id)

    # Fast path: both org and user already known — skip all DB work.
    if org_key in _known_orgs and user_key in _known_users:
        return

    meta = metadata or {}
    await ensure_organization_row(
        db,
        auth.org_id,
        org_name=meta.get("org_name") if isinstance(meta.get("org_name"), str) else None,
    )
    await db.flush()

    now = datetime.now(timezone.utc)
    result = await db.execute(select(User).where(User.id == auth.user_id))
    user = result.scalar_one_or_none()

    full_name = meta.get("full_name")
    job_title = meta.get("job_title")

    changed = False

    if user:
        if user.org_id != auth.org_id:
            user.org_id = auth.org_id
            changed = True
        if user.role != auth.role:
            user.role = auth.role
            changed = True
        if auth.email and user.email != auth.email:
            user.email = auth.email
            changed = True
        if isinstance(full_name, str) and full_name.strip() and user.full_name != full_name.strip():
            user.full_name = full_name.strip()
            changed = True
        if isinstance(job_title, str) and job_title.strip() and user.job_title != job_title.strip():
            user.job_title = job_title.strip()
            changed = True
        # Always update last_login_at but only commit if something else changed
        # to avoid a write on every read-only request.
        user.last_login_at = now
    else:
        await db.execute(
            pg_insert(User)
            .values(
                id=auth.user_id,
                email=auth.email or f"{auth.user_id}@local.dev",
                role=auth.role,
                org_id=auth.org_id,
                full_name=full_name.strip() if isinstance(full_name, str) else None,
                job_title=job_title.strip() if isinstance(job_title, str) else None,
                last_login_at=now,
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
        result = await db.execute(select(User).where(User.id == auth.user_id))
        user = result.scalar_one_or_none()
        if user:
            user.org_id = auth.org_id
            user.role = auth.role
            user.last_login_at = now
            if auth.email:
                user.email = auth.email
        changed = True

    if changed:
        await db.commit()
    else:
        # Roll back any pending flush so the session stays clean for read-only
        # requests (avoids an implicit commit on session close).
        await db.rollback()

    # Mark as known so subsequent requests skip the DB entirely.
    _known_orgs.add(org_key)
    _known_users.add(user_key)
