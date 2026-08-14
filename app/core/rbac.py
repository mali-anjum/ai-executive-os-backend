"""
Centralized organization RBAC.

Single place that decides which roles may perform organization administration
(create/revoke invitations, manage members, edit org settings) versus which may
only read their own membership. Route guards stay thin; permission policy lives
here so it is never scattered across components or routes.

Role hierarchy (matches the frontend `getRolePermissions` / `tenancy.ts`):
    owner  → full authority (Org Owner)
    admin  → full authority (Org Admin)
    manager → leadership but NOT member administration
    employee → member only
"""
from __future__ import annotations

from app.models.http.enums import UserRole

# Roles allowed to manage members / invitations / org settings.
_MEMBER_ADMIN_ROLES: frozenset[UserRole] = frozenset({"owner", "admin"})
# Roles with leadership visibility (analytics, summaries).
_LEADERSHIP_ROLES: frozenset[UserRole] = frozenset({"owner", "admin", "manager"})


def can_manage_members(role: UserRole) -> bool:
    """Owner/Admin only — invite, revoke, assign roles, edit org settings."""
    return role in _MEMBER_ADMIN_ROLES


def can_assign_role(assigner: UserRole, target_role: UserRole) -> bool:
    """Only an owner may grant/assign the owner role; admins cannot escalate."""
    if target_role == "owner":
        return assigner == "owner"
    return can_manage_members(assigner)


def is_leadership(role: UserRole) -> bool:
    return role in _LEADERSHIP_ROLES


def member_admin_roles() -> frozenset[str]:
    return frozenset(_MEMBER_ADMIN_ROLES)
