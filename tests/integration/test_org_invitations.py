import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.http.schemas import AcceptInvitationResponse, InvitationResponse

ORG_1 = uuid.uuid4()
ORG_2 = uuid.uuid4()


@pytest.fixture(autouse=True)
def _dev_auth_mode(monkeypatch):
    """Route auth resolves dev X-Org-Id/X-User-Id headers in development mode."""
    from app.core.config import settings as cfg

    monkeypatch.setattr(cfg, "app_env", "development")


def _auth(org_id, role, user_id=None):
    return {
        "X-Org-Id": str(org_id),
        "X-User-Id": str(user_id or uuid.uuid4()),
        "X-User-Role": role,
    }


OWNER = _auth(ORG_1, "owner")
ADMIN = _auth(ORG_1, "admin")
MANAGER = _auth(ORG_1, "manager")
EMPLOYEE = _auth(ORG_1, "employee")
ORG2_OWNER = _auth(ORG_2, "owner")


@pytest.mark.asyncio
@patch("app.api.v1.routers.orgs.OrganizationService.create_invitation", new_callable=AsyncMock)
async def test_invite_requires_owner_or_admin(mock_create, client):
    mock_create.return_value = InvitationResponse(
        id=uuid.uuid4(),
        org_id=ORG_1,
        email="jane@acme.com",
        role="employee",
        status="pending",
        expires_at="2099-01-01T00:00:00Z",
        created_at="2026-01-01T00:00:00Z",
    )

    # Owner and admin may create an invitation.
    ok = await client.post(
        "/api/v1/orgs/me/invitations",
        json={"email": "jane@acme.com", "role": "employee"},
        headers=OWNER,
    )
    assert ok.status_code == 200, ok.text

    ok_admin = await client.post(
        "/api/v1/orgs/me/invitations",
        json={"email": "jill@acme.com", "role": "employee"},
        headers=ADMIN,
    )
    assert ok_admin.status_code == 200, ok_admin.text

    # Manager and employee are denied — authorization not visibility.
    for headers in (MANAGER, EMPLOYEE):
        res = await client.post(
            "/api/v1/orgs/me/invitations",
            json={"email": "x@acme.com", "role": "employee"},
            headers=headers,
        )
        assert res.status_code == 403, res.text


@pytest.mark.asyncio
@patch("app.api.v1.routers.orgs.OrganizationService.accept_invitation", new_callable=AsyncMock)
async def test_accept_invitation_flows_to_service(mock_accept, client):
    mock_accept.return_value = AcceptInvitationResponse(
        org_id=ORG_1,
        org_name="Acme",
        org_slug="acme",
        role="employee",
    )
    res = await client.post("/api/v1/invitations/accept", headers=OWNER)
    assert res.status_code == 200, res.text
    assert res.json()["org_id"] == str(ORG_1)
    assert res.json()["role"] == "employee"


@pytest.mark.asyncio
@patch("app.api.v1.routers.orgs.OrganizationService.revoke_invitation", new_callable=AsyncMock)
async def test_revoke_invitation_requires_admin(mock_revoke, client):
    # Any authenticated owner/admin may call; service scopes the query to the
    # caller's org (`org_id == auth.org_id`) and the require_admin dependency
    # blocks manager/employee before the service runs.
    res_owner = await client.delete(
        f"/api/v1/orgs/me/invitations/{uuid.uuid4()}", headers=OWNER
    )
    assert res_owner.status_code == 204, res_owner.text

    # Same-org employee still cannot revoke (require_admin).
    res_emp = await client.delete(
        f"/api/v1/orgs/me/invitations/{uuid.uuid4()}", headers=EMPLOYEE
    )
    assert res_emp.status_code == 403, res_emp.text

    mock_revoke.assert_awaited_once()

