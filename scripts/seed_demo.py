#!/usr/bin/env python3
"""CLI: seed demo SOPs and sample activity for the first org admin."""

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db.tables import Organization, User
from app.services.demo_seed_service import DemoSeedService


async def main() -> int:
    async with AsyncSessionLocal() as db:
        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalar_one_or_none()
        if not org:
            print("No organization found. Sign up first.", file=sys.stderr)
            return 1

        user_result = await db.execute(
            select(User).where(User.org_id == org.id, User.role == "admin").limit(1)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            user_result = await db.execute(
                select(User).where(User.org_id == org.id).limit(1)
            )
            user = user_result.scalar_one_or_none()
        if not user:
            print("No user found for org.", file=sys.stderr)
            return 1

        service = DemoSeedService()
        result = await service.seed_org(
            db,
            org_id=org.id,
            user_id=user.id if isinstance(user.id, uuid.UUID) else uuid.UUID(str(user.id)),
        )
        print(result["message"])
        print(
            f"Documents queued: {result['documents_queued']}, "
            f"sample queries: {result['sample_queries']}, "
            f"tickets: {result['sample_tickets']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
