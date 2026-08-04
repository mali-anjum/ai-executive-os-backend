"""Authenticated request identity passed into routes and services."""

import uuid
from dataclasses import dataclass

from app.models.http.enums import UserRole


@dataclass
class AuthContext:
    """Who is calling the API — user, org, and role for tenant scoping."""

    user_id: uuid.UUID
    org_id: uuid.UUID
    role: UserRole
    email: str | None = None
