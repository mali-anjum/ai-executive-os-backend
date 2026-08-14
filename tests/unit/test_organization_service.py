from datetime import datetime, timedelta, timezone

from app.models.db.tables import Organization, OrganizationInvitation
from app.services.organization_service import (
    _effective_status,
    _normalize_email,
    _onboarding_completed,
)


def test_normalize_email_lowercases_and_trims() -> None:
    assert _normalize_email("  Alice@Acme.COM ") == "alice@acme.com"


def test_effective_status_expired_when_past_due() -> None:
    invitation = OrganizationInvitation(
        status="pending",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    assert _effective_status(invitation, datetime.now(timezone.utc)) == "expired"


def test_effective_status_pending_when_not_expired() -> None:
    invitation = OrganizationInvitation(
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    assert _effective_status(invitation, datetime.now(timezone.utc)) == "pending"


def test_effective_status_keeps_accepted_and_revoked() -> None:
    now = datetime.now(timezone.utc)
    accepted = OrganizationInvitation(status="accepted", expires_at=now)
    revoked = OrganizationInvitation(status="revoked", expires_at=now)
    assert _effective_status(accepted, now) == "accepted"
    assert _effective_status(revoked, now) == "revoked"


def test_onboarding_completed_reads_settings_json() -> None:
    done = Organization(settings_json={"onboarding": {"completed": True}})
    not_done = Organization(settings_json={"onboarding": {"completed": False}})
    none = Organization(settings_json=None)
    assert _onboarding_completed(done) is True
    assert _onboarding_completed(not_done) is False
    assert _onboarding_completed(none) is False
