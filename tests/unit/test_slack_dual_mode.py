from app.core.slack_events import (
    is_slack_qa_message,
    is_slack_ticket_message,
    slack_message_mode,
)


def test_question_routes_to_qa():
    event = {"type": "message", "text": "How many PTO days do I get?"}
    assert slack_message_mode(event) == "qa"
    assert is_slack_qa_message(event) is True
    assert is_slack_ticket_message(event) is False


def test_ticket_prefix_routes_to_ticket():
    event = {"type": "message", "text": "!ticket VPN is broken for the sales team"}
    assert slack_message_mode(event) == "ticket"
    assert is_slack_ticket_message(event) is True
    assert is_slack_qa_message(event) is False


def test_urgent_statement_routes_to_ticket():
    event = {"type": "message", "text": "Production database is down asap"}
    assert slack_message_mode(event) == "ticket"
