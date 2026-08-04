"""Jira REST API v3 — create issues after ticket approval."""

from __future__ import annotations

import logging
import uuid

import httpx

from app.core.encryption import decrypt_value
from app.models.db.tables import Ticket

logger = logging.getLogger(__name__)


class JiraService:
    """Minimal Jira client using site URL + email + API token from org integrations."""

    async def create_issue(
        self,
        *,
        site_url: str,
        email: str,
        api_token: str,
        ticket: Ticket,
        project_key: str,
    ) -> str | None:
        base = site_url.rstrip("/")
        url = f"{base}/rest/api/3/issue"
        summary = ticket.summary or ticket.title or "AI-routed ticket"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary[:255],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Intent: {ticket.intent}\n"
                                        f"Priority: P{ticket.priority}\n"
                                        f"Department: {ticket.department}\n"
                                        f"Source: {ticket.source}\n"
                                        f"Ticket ID: {ticket.id}"
                                    ),
                                }
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Task"},
            }
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    url,
                    json=payload,
                    auth=(email, api_token),
                    headers={"Accept": "application/json"},
                )
                res.raise_for_status()
                data = res.json()
                return str(data.get("key") or data.get("id") or "")
        except Exception:
            logger.exception("jira_create_issue_failed ticket_id=%s", ticket.id)
            return None

    @staticmethod
    def parse_config(config_encrypted: str) -> dict[str, str]:
        import json

        plain = decrypt_value(config_encrypted)
        if not plain:
            return {}
        return json.loads(plain)
