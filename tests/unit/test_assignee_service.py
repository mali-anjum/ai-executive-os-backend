import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.db.tables import User
from app.services.assignee_service import AssigneeService


@pytest.mark.asyncio
async def test_round_robin_cycles_users(monkeypatch):
    class _Flags:
        WORKLOAD_BALANCING_ENABLED = False

    monkeypatch.setattr("app.services.assignee_service.flags", _Flags())
    org_id = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    mapping = MagicMock()
    mapping.user_ids = [str(user_a), str(user_b)]
    mapping.round_robin_index = 0

    user_obj_a = User(
        id=user_a,
        email="a@test.com",
        role="employee",
        org_id=org_id,
        slack_user_id="U1",
    )
    user_obj_b = User(
        id=user_b,
        email="b@test.com",
        role="employee",
        org_id=org_id,
        slack_user_id="U2",
    )

    db = AsyncMock()

    async def fake_execute(stmt):
        result = MagicMock()
        call_count = fake_execute.calls
        fake_execute.calls += 1
        if call_count == 0:
            result.scalar_one_or_none.return_value = mapping
        elif call_count == 1:
            result.scalar_one_or_none.return_value = user_obj_a
        elif call_count == 2:
            result.scalar_one_or_none.return_value = mapping
        elif call_count == 3:
            result.scalar_one_or_none.return_value = user_obj_b
        return result

    fake_execute.calls = 0
    db.execute = fake_execute
    db.commit = AsyncMock()

    service = AssigneeService()
    first = await service.assign_round_robin(db, org_id, "billing")
    second = await service.assign_round_robin(db, org_id, "billing")

    assert first.id == user_a
    assert second.id == user_b
