"""Slack Events API payload shapes (subset we handle)."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class SlackMessageEvent(TypedDict, total=False):
    type: str
    subtype: str
    channel: str
    ts: str
    text: str
    bot_id: str
    blocks: list[dict[str, Any]]


class SlackEventCallbackPayload(TypedDict, total=False):
    type: str
    challenge: str
    event_id: str
    event: SlackMessageEvent
