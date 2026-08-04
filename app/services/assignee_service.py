"""Round-robin assignee pick per department — maps tickets to org users."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import flags
from app.models.db.tables import AssigneeMapping, Ticket, User

_OPEN_STATUSES = ("open", "in_progress", "pending_approval")


class AssigneeService:
    """Uses AssigneeMapping rows; seeds defaults on first ticket in an org."""

    async def assign_round_robin(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        department: str,
    ) -> User | None:
        dept = department.lower()
        result = await db.execute(
            select(AssigneeMapping).where(
                AssigneeMapping.org_id == org_id,
                AssigneeMapping.department == dept,
            )
        )
        mapping = result.scalar_one_or_none()

        if not mapping or not mapping.user_ids:
            result = await db.execute(
                select(User).where(
                    User.org_id == org_id,
                    User.department == dept,
                )
            )
            users = list(result.scalars().all())
            if not users:
                result = await db.execute(
                    select(User).where(User.org_id == org_id).limit(1)
                )
                return result.scalar_one_or_none()
            candidate_ids = [u.id for u in users]
            chosen_id = (
                await self._pick_by_workload(db, org_id, candidate_ids)
                if flags.WORKLOAD_BALANCING_ENABLED
                else candidate_ids[0]
            )
            user_result = await db.execute(select(User).where(User.id == chosen_id))
            return user_result.scalar_one_or_none()

        user_ids = [uuid.UUID(str(uid)) for uid in mapping.user_ids]
        if flags.WORKLOAD_BALANCING_ENABLED:
            chosen_id = await self._pick_by_workload(db, org_id, user_ids)
        else:
            idx = mapping.round_robin_index % len(user_ids)
            chosen_id = user_ids[idx]
            mapping.round_robin_index = (idx + 1) % len(user_ids)
            await db.commit()

        user_result = await db.execute(select(User).where(User.id == chosen_id))
        return user_result.scalar_one_or_none()

    async def _pick_by_workload(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        user_ids: list[uuid.UUID],
    ) -> uuid.UUID:
        loads: dict[uuid.UUID, int] = {}
        for user_id in user_ids:
            count_result = await db.execute(
                select(func.count())
                .select_from(Ticket)
                .where(
                    Ticket.org_id == org_id,
                    Ticket.assignee_id == user_id,
                    Ticket.status.in_(_OPEN_STATUSES),
                )
            )
            loads[user_id] = int(count_result.scalar_one())
        return min(user_ids, key=lambda uid: loads.get(uid, 0))

    async def ensure_default_mappings(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> None:
        defaults = {
            "engineering": [],
            "billing": [],
            "hr": [],
            "product": [],
            "support": [],
        }
        for dept in defaults:
            result = await db.execute(
                select(AssigneeMapping).where(
                    AssigneeMapping.org_id == org_id,
                    AssigneeMapping.department == dept,
                )
            )
            if result.scalar_one_or_none():
                continue
            users_result = await db.execute(
                select(User).where(User.org_id == org_id, User.department == dept)
            )
            user_ids = [str(u.id) for u in users_result.scalars().all()]
            if not user_ids:
                any_users = await db.execute(
                    select(User).where(User.org_id == org_id).limit(3)
                )
                user_ids = [str(u.id) for u in any_users.scalars().all()]
            if user_ids:
                db.add(
                    AssigneeMapping(
                        org_id=org_id,
                        department=dept,
                        user_ids=user_ids,
                        round_robin_index=0,
                    )
                )
        await db.commit()
