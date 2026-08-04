"""
Pure parsing rules for Slack → ticket pipeline (no I/O).

webhooks.py filters with should_process_slack_message; ProjectAgent splits multi-line
posts here. Keeps Slack payload shape out of agents and services.
"""

from __future__ import annotations

import re

from app.models.http.slack import SlackEventCallbackPayload, SlackMessageEvent

_MIN_TICKET_LINE_LEN = 12
_LINE_PREFIX = re.compile(r"^[-*•]\s*|\d+[.)]\s*")

# Subtypes we must not turn into tickets (edits, deletes, joins, bot posts).
_IGNORED_MESSAGE_SUBTYPES = frozenset(
    {
        "bot_message",
        "message_changed",
        "message_deleted",
        "channel_join",
        "channel_leave",
        "channel_topic",
        "channel_purpose",
        "channel_name",
        "channel_archive",
        "channel_unarchive",
        "group_join",
        "group_leave",
        "ekm_access_denied",
    }
)


def extract_message_text(event: SlackMessageEvent) -> str:
    """Plain text from a Slack message event, including simple block fallbacks."""
    text = (event.get("text") or "").strip()
    if text:
        return text

    parts: list[str] = []
    for block in event.get("blocks") or []:
        if block.get("type") != "rich_text":
            continue
        for element in block.get("elements") or []:
            if element.get("type") != "rich_text_section":
                continue
            for item in element.get("elements") or []:
                if item.get("type") == "text":
                    piece = (item.get("text") or "").strip()
                    if piece:
                        parts.append(piece)
    return "\n".join(parts).strip()


def split_message_into_ticket_lines(text: str) -> list[str]:
    """
    One Slack message can contain several requests on separate lines.
    Returns multiple lines for multi-request posts; otherwise a single item.
    """
    stripped = text.strip()
    if not stripped:
        return []

    lines: list[str] = []
    for raw in stripped.splitlines():
        line = _LINE_PREFIX.sub("", raw.strip()).strip()
        if len(line) >= _MIN_TICKET_LINE_LEN:
            lines.append(line)

    if len(lines) >= 2:
        return lines
    return [stripped]


def slack_message_ts_for_line(base_ts: str, line_index: int, *, multi_line: bool) -> str:
    """Unique DB key per line when one Slack post becomes several tickets."""
    if not multi_line:
        return base_ts
    return f"{base_ts}#{line_index}"


_QUESTION_PREFIXES = (
    "how ",
    "what ",
    "why ",
    "when ",
    "who ",
    "where ",
    "can ",
    "is ",
    "does ",
    "do ",
    "could ",
    "should ",
)


_TICKET_PREFIXES = (
    "!ticket",
    "!route",
    "urgent:",
    "action:",
    "please fix",
    "please assign",
    "create ticket",
    "need help with",
)


def is_slack_ticket_message(event: SlackMessageEvent) -> bool:
    """True when the message should route to Project Agent (ticket creation)."""
    text = extract_message_text(event).strip().lower()
    if not text:
        return False
    if text.startswith("!ticket") or text.startswith("!route"):
        return True
    for phrase in _TICKET_PREFIXES:
        if phrase.startswith("!"):
            continue
        if phrase in text:
            return True
    # Statements without question marks that look like work requests
    if "?" not in text and any(
        kw in text
        for kw in ("broken", "not working", "down", "outage", "asap", "escalate")
    ):
        return True
    return False


def is_slack_qa_message(event: SlackMessageEvent) -> bool:
    """True when the message looks like a knowledge question (in-channel Q&A)."""
    if is_slack_ticket_message(event):
        return False
    if event.get("subtype") == "app_mention":
        return True
    text = extract_message_text(event).strip().lower()
    if not text:
        return False
    if text.endswith("?"):
        return True
    return any(text.startswith(prefix) for prefix in _QUESTION_PREFIXES)


def slack_message_mode(event: SlackMessageEvent) -> str:
    """Dual-mode routing: 'qa' for knowledge answers, 'ticket' for project routing."""
    if is_slack_ticket_message(event):
        return "ticket"
    if is_slack_qa_message(event):
        return "qa"
    return "ticket"


def should_process_slack_message(event: SlackMessageEvent) -> bool:
    """True when this event should create (or dedupe) a ticket."""
    if event.get("type") != "message":
        return False
    if event.get("bot_id"):
        return False
    subtype = event.get("subtype")
    if subtype in _IGNORED_MESSAGE_SUBTYPES:
        return False
    if not event.get("channel") or not event.get("ts"):
        return False
    return bool(extract_message_text(event))


def slack_dedupe_key(
    payload: SlackEventCallbackPayload, event: SlackMessageEvent
) -> str:
    """Stable idempotency key for a single Slack delivery."""
    event_id = payload.get("event_id")
    if event_id:
        return str(event_id)
    channel = event.get("channel")
    ts = event.get("ts")
    return f"{channel}:{ts}"
