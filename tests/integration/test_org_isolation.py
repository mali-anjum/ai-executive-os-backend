import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.http.schemas import QueryResponse

ORG_1 = uuid.uuid4()
ORG_2 = uuid.uuid4()
USER_1 = uuid.uuid4()
USER_2 = uuid.uuid4()

AUTH_ORG_1 = {
    "X-Org-Id": str(ORG_1),
    "X-User-Id": str(USER_1),
    "X-User-Role": "employee",
}
AUTH_ORG_2 = {
    "X-Org-Id": str(ORG_2),
    "X-User-Id": str(USER_2),
    "X-User-Role": "employee",
}


@pytest.mark.asyncio
@patch("app.api.v1.routers.query.KnowledgeAgent.run", new_callable=AsyncMock)
async def test_org1_query_does_not_use_org2_retrieval(mock_run, client):
    mock_run.return_value = QueryResponse(answer="ok", citations=[], latency_ms=1)
    org_ids: list[uuid.UUID | None] = []

    async def capture(*args, **kwargs):
        org_ids.append(kwargs.get("org_id"))
        return QueryResponse(answer="ok", citations=[], latency_ms=1)

    mock_run.side_effect = capture

    await client.post(
        "/api/v1/query",
        json={"query": "PTO policy"},
        headers=AUTH_ORG_1,
    )
    await client.post(
        "/api/v1/query",
        json={"query": "PTO policy"},
        headers=AUTH_ORG_2,
    )

    assert len(org_ids) == 2
    assert org_ids[0] == ORG_1
    assert org_ids[1] == ORG_2
    assert org_ids[0] != org_ids[1]
