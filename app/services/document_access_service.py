"""Document-level RBAC — filter retrieval by user role and department."""

from __future__ import annotations

from sqlalchemy import or_

from sqlalchemy import true
from app.models.db.tables import Document


class DocumentAccessService:
    """Build SQL filters so users only retrieve chunks they may access."""

    def can_access_document(
        self,
        document: Document,
        *,
        role: str,
        department: str | None,
    ) -> bool:
        if role == "admin":
            return True
        allowed_roles = document.allowed_roles or []
        if allowed_roles and role not in allowed_roles:
            return False
        allowed_depts = document.allowed_departments or []
        if allowed_depts and (not department or department not in allowed_depts):
            return False
        return True

    def sqlalchemy_access_filter(self, *, role: str, department: str | None):
        """Admin sees all org docs; others must match allowed_roles / allowed_departments."""
        if role == "admin":
            return true()

        role_match = or_(
            Document.allowed_roles.is_(None),
            Document.allowed_roles == [],
            Document.allowed_roles.contains([role]),
        )
        if department:
            dept_match = or_(
                Document.allowed_departments.is_(None),
                Document.allowed_departments == [],
                Document.allowed_departments.contains([department]),
            )
        else:
            dept_match = or_(
                Document.allowed_departments.is_(None),
                Document.allowed_departments == [],
            )
        return role_match & dept_match
