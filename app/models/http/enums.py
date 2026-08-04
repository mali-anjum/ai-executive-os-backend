"""Shared string enums for API and domain — keeps OpenAPI + pyright unambiguous."""

from typing import Literal

AiProviderId = Literal["openai", "anthropic", "gemini", "groq"]
UserRole = Literal["admin", "manager", "employee"]
DocumentStatus = Literal["pending", "processing", "ready", "error"]
TicketStatus = Literal[
    "open", "in_progress", "resolved", "closed", "pending_approval"
]
TicketSource = Literal["slack", "manual", "api"]
ApprovalStatus = Literal["auto_approved", "pending", "pending_approval", "approved", "rejected"]
