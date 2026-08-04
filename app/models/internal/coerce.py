"""Narrow DB / external strings into API Literal types."""

from __future__ import annotations

from typing import cast

from app.models.http.enums import (
    AiProviderId,
    DocumentStatus,
    TicketSource,
    TicketStatus,
    UserRole,
)


def as_document_status(value: str) -> DocumentStatus:
    if value in ("pending", "processing", "ready", "error"):
        return cast(DocumentStatus, value)
    return "pending"


def as_ticket_source(value: str) -> TicketSource:
    if value in ("slack", "manual", "api"):
        return cast(TicketSource, value)
    return "manual"


def as_ticket_status(value: str) -> TicketStatus:
    if value in ("open", "in_progress", "resolved", "closed", "pending_approval"):
        return cast(TicketStatus, value)
    return "open"


def as_ai_provider_id(value: str) -> AiProviderId:
    if value in ("openai", "anthropic", "gemini", "groq"):
        return cast(AiProviderId, value)
    return "gemini"


def as_user_role(value: str) -> UserRole:
    if value == "admin":
        return "admin"
    if value == "manager":
        return "manager"
    return "employee"
