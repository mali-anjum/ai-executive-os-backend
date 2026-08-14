"""
Organization context, members, invitations, and onboarding.

Membership is modeled by `users.org_id` + `users.role` (no separate join table —
see MULTI_TENANCY.md). All queries are scoped to the authenticated organization
(`auth.org_id`); the frontend-supplied org boundary is never trusted here.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.core.rbac import can_assign_role, can_manage_members
from app.models.db.tables import (
    Organization,
    OrganizationInvitation,
    User,
)
from app.models.http.enums import InvitationStatus, UserRole
from app.models.http.schemas import (
    AcceptInvitationResponse,
    InvitationResponse,
    MemberResponse,
    OrgContextResponse,
    OrganizationResponse,
)
from app.models.internal.coerce import as_user_role

_ONBOARDING_KEY = "onboarding"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _as_invitation_status(value: str) -> InvitationStatus:
    if value in ("accepted", "revoked", "expired"):
        return _cast_status(value)
    return "pending"


def _cast_status(value: str) -> InvitationStatus:
    # Narrowing helper for Literal typing.
    if value == "accepted":
        return "accepted"
    if value == "revoked":
        return "revoked"
    if value == "expired":
        return "expired"
    return "pending"


def _effective_status(
    invitation: OrganizationInvitation, now: datetime
) -> InvitationStatus:
    if invitation.status == "pending" and invitation.expires_at <= now:
        return "expired"
    return _as_invitation_status(invitation.status)


def _to_invitation_response(
    invitation: OrganizationInvitation,
    now: datetime,
) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        org_id=invitation.org_id,
        email=invitation.email,
        role=as_user_role(invitation.role),
        department=invitation.department,
        status=_effective_status(invitation, now),
        expires_at=invitation.expires_at,
        invited_by=invitation.invited_by,
        accepted_at=invitation.accepted_at,
        created_at=invitation.created_at,
    )


def _onboarding_completed(org: Organization) -> bool:
    settings = org.settings_json or {}
    onboarding = settings.get(_ONBOARDING_KEY)
    if isinstance(onboarding, dict):
        return bool(onboarding.get("completed", False))
    return False


class OrganizationService:
    """All organization-level operations, scoped by the authenticated org."""

    async def get_context(self, db: AsyncSession, auth: AuthContext) -> OrgContextResponse:
        org = await self._get_org(db, auth)
        return OrgContextResponse(
            org=OrganizationResponse.model_validate(org),
            role=auth.role,
            onboarding_completed=_onboarding_completed(org),
        )

    async def _get_org(self, db: AsyncSession, auth: AuthContext) -> Organization:
        result = await db.execute(
            select(Organization).where(Organization.id == auth.org_id)
        )
        org = result.scalar_one_or_none()
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )
        return org

    async def update_org(
        self,
        db: AsyncSession,
        auth: AuthContext,
        *,
        name: str | None,
        industry: str | None,
        website: str | None,
        timezone: str | None,
        logo_url: str | None,
    ) -> OrganizationResponse:
        if not can_manage_members(auth.role):
            self._forbidden()
        org = await self._get_org(db, auth)
        if name is not None:
            org.name = name
        if industry is not None:
            org.industry = industry
        if website is not None:
            org.website = website
        if timezone is not None:
            org.timezone = timezone
        if logo_url is not None:
            org.logo_url = logo_url
        await db.commit()
        await db.refresh(org)
        return OrganizationResponse.model_validate(org)

    async def update_onboarding(
        self,
        db: AsyncSession,
        auth: AuthContext,
        *,
        completed: bool,
        step: str | None,
    ) -> bool:
        org = await self._get_org(db, auth)
        settings = dict(org.settings_json or {})
        onboarding = dict(settings.get(_ONBOARDING_KEY, {}) or {})
        onboarding["completed"] = completed
        if step:
            onboarding["last_step"] = step
        onboarding["updated_at"] = datetime.now(timezone.utc).isoformat()
        settings[_ONBOARDING_KEY] = onboarding
        org.settings_json = settings
        await db.commit()
        return _onboarding_completed(org)

    async def list_members(self, db: AsyncSession, auth: AuthContext) -> list[MemberResponse]:
        result = await db.execute(
            select(User)
            .where(User.org_id == auth.org_id, User.is_active.is_(True))
            .order_by(User.created_at)
        )
        members = result.scalars().all()
        return [
            MemberResponse(
                id=m.id,
                email=m.email,
                full_name=m.full_name,
                job_title=m.job_title,
                role=as_user_role(m.role),
                department=m.department,
                org_id=m.org_id or auth.org_id,
                created_at=m.created_at,
            )
            for m in members
        ]

    async def create_invitation(
        self,
        db: AsyncSession,
        auth: AuthContext,
        *,
        email: str,
        role: UserRole,
        department: str | None,
        expires_in_days: int,
    ) -> InvitationResponse:
        if not can_manage_members(auth.role):
            self._forbidden()
        if not can_assign_role(auth.role, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the organization owner may assign the owner role",
            )
        normalized = _normalize_email(email)
        now = datetime.now(timezone.utc)

        # A user already in this org cannot be re-invited into it.
        existing = await db.execute(
            select(User).where(
                User.org_id == auth.org_id,
                User.email == normalized,
                User.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already a member of the organization",
            )

        duplicate = await db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.org_id == auth.org_id,
                OrganizationInvitation.email == normalized,
                OrganizationInvitation.status == "pending",
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this email",
            )

        invitation = OrganizationInvitation(
            id=uuid.uuid4(),
            org_id=auth.org_id,
            email=normalized,
            role=role,
            department=department,
            token=secrets.token_urlsafe(48),
            status="pending",
            expires_at=now + timedelta(days=expires_in_days),
            invited_by=auth.user_id,
        )
        db.add(invitation)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pending invitation already exists for this email",
            ) from None
        await db.refresh(invitation)
        return _to_invitation_response(invitation, now)

    async def list_invitations(
        self, db: AsyncSession, auth: AuthContext
    ) -> list[InvitationResponse]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.org_id == auth.org_id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        return [_to_invitation_response(inv, now) for inv in result.scalars().all()]

    async def revoke_invitation(
        self, db: AsyncSession, auth: AuthContext, invitation_id: uuid.UUID
    ) -> None:
        if not can_manage_members(auth.role):
            self._forbidden()
        result = await db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.id == invitation_id,
                OrganizationInvitation.org_id == auth.org_id,
            )
        )
        invitation = result.scalar_one_or_none()
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found",
            )
        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending invitations can be revoked",
            )
        invitation.status = "revoked"
        await db.commit()

    async def accept_invitation(
        self, db: AsyncSession, auth: AuthContext
    ) -> AcceptInvitationResponse | None:
        """Join the org invited to `auth.email` — never create a new one.

        Finds the caller's pending, unexpired invitation, applies the membership
        (org + role), marks it accepted, and returns the resulting org context so
        the client can sync its Supabase `user_metadata`.
        """
        if not auth.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authenticated user has no email to match an invitation",
            )
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.email == _normalize_email(auth.email),
                OrganizationInvitation.status == "pending",
            )
        )
        invitations = result.scalars().all()
        # Only accept if unexpired; ignore stale rows.
        pending = [inv for inv in invitations if inv.expires_at > now]
        if not pending:
            return None

        invitation = pending[0]
        role = as_user_role(invitation.role)

        # Provision / move this user into the invited org with the assigned role.
        user_result = await db.execute(select(User).where(User.id == auth.user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                id=auth.user_id,
                email=_normalize_email(auth.email),
                role=role,
                org_id=invitation.org_id,
                department=invitation.department,
            )
            db.add(user)
        else:
            user.org_id = invitation.org_id
            user.role = role
            user.email = _normalize_email(auth.email)
            if invitation.department:
                user.department = invitation.department

        invitation.status = "accepted"
        invitation.accepted_at = now

        await db.commit()

        org_result = await db.execute(
            select(Organization).where(Organization.id == invitation.org_id)
        )
        org = org_result.scalar_one()
        return AcceptInvitationResponse(
            org_id=org.id,
            org_name=org.name,
            org_slug=org.slug,
            role=role,
        )

    @staticmethod
    def _forbidden() -> None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner or admin role required",
        )
