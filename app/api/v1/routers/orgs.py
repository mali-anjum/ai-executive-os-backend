"""
Organization context, members, invitations, and onboarding (Sprint 4).

Auth boundary: every route derives the org from the authenticated user
(get_current_user / require_admin) — never from a frontend-supplied org id.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.core.database import get_db
from app.core.feature_flags import flags
from app.core.security import get_current_user, require_admin, tenant_org_id
from app.models.http.schemas import (
    AcceptInvitationResponse,
    InvitationCreateRequest,
    InvitationResponse,
    MemberResponse,
    OnboardingUpdateRequest,
    OrgContextResponse,
    OrgUpdateRequest,
    OrganizationResponse,
)
from app.services.organization_service import OrganizationService

router = APIRouter()
service = OrganizationService()


def _management_enabled() -> None:
    if not flags.ORG_MANAGEMENT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization management is not enabled",
        )


@router.get("/orgs/me", response_model=OrgContextResponse)
async def get_org_context(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgContextResponse:
    return await service.get_context(db, auth)


@router.patch("/orgs/me", response_model=OrganizationResponse)
async def update_org(
    body: OrgUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    return await service.update_org(
        db,
        auth,
        name=body.name,
        industry=body.industry,
        website=body.website,
        timezone=body.timezone,
        logo_url=body.logo_url,
    )


@router.patch("/orgs/me/onboarding")
async def update_onboarding(
    body: OnboardingUpdateRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    completed = await service.update_onboarding(
        db,
        auth,
        completed=body.completed,
        step=body.step,
    )
    return {"completed": completed}


@router.get("/orgs/me/members", response_model=list[MemberResponse])
async def list_members(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _org_id: uuid.UUID | None = Depends(tenant_org_id),
) -> list[MemberResponse]:
    return await service.list_members(db, auth)


@router.post("/orgs/me/invitations", response_model=InvitationResponse)
async def create_invitation(
    body: InvitationCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    _management_enabled()
    return await service.create_invitation(
        db,
        auth,
        email=body.email,
        role=body.role,
        department=body.department,
        expires_in_days=body.expires_in_days,
    )


@router.get("/orgs/me/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[InvitationResponse]:
    _management_enabled()
    return await service.list_invitations(db, auth)


@router.delete("/orgs/me/invitations/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    _management_enabled()
    await service.revoke_invitation(db, auth, invitation_id)


@router.post("/invitations/accept", response_model=AcceptInvitationResponse | None)
async def accept_invitation(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AcceptInvitationResponse | None:
    _management_enabled()
    return await service.accept_invitation(db, auth)
