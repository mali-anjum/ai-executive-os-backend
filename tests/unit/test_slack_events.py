import json
from pathlib import Path

from app.core.slack_events import (
    extract_message_text,
    should_process_slack_message,
    slack_dedupe_key,
    slack_message_ts_for_line,
    split_message_into_ticket_lines,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_should_process_fixture_message():
    payload = json.loads((FIXTURES / "slack_message_event.json").read_text())
    event = payload["event"]
    assert should_process_slack_message(event) is True
    assert extract_message_text(event) == event["text"]


def test_ignores_bot_message():
    assert (
        should_process_slack_message(
            {"type": "message", "subtype": "bot_message", "text": "hi", "channel": "C1", "ts": "1.0"}
        )
        is False
    )


def test_ignores_message_changed():
    assert (
        should_process_slack_message(
            {
                "type": "message",
                "subtype": "message_changed",
                "text": "hi",
                "channel": "C1",
                "ts": "1.0",
            }
        )
        is False
    )


def test_extract_text_from_blocks():
    event = {
        "type": "message",
        "channel": "C1",
        "ts": "1.0",
        "blocks": [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [{"type": "text", "text": "From blocks only"}],
                    }
                ],
            }
        ],
    }
    assert extract_message_text(event) == "From blocks only"
    assert should_process_slack_message(event) is True


def test_split_multi_line_message_into_separate_tickets():
    text = (
        "Add dark mode toggle in settings page\n"
        "Need export to CSV feature for analytics dashboard\n"
        "Can we improve onboarding flow? Users are dropping after signup"
    )
    lines = split_message_into_ticket_lines(text)
    assert len(lines) == 3


def test_single_line_message_stays_one_ticket():
    assert split_message_into_ticket_lines("Slack test ticket June 5") == [
        "Slack test ticket June 5"
    ]


def test_slack_message_ts_for_line_index():
    assert slack_message_ts_for_line("1780622422.178879", 2, multi_line=True) == (
        "1780622422.178879#2"
    )


def test_dedupe_key_prefers_event_id():
    payload = {"event_id": "Ev123", "event": {"channel": "C1", "ts": "1.0"}}
    assert slack_dedupe_key(payload, payload["event"]) == "Ev123"
