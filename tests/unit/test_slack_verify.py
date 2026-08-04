import pytest
from fastapi import HTTPException

from app.core.slack_verify import verify_slack_signature
from tests.helpers.slack_signing import sign_slack_request

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr("app.core.slack_verify.settings.slack_signing_secret", SECRET)


def test_valid_signature_passes():
    body = b'{"type":"url_verification","challenge":"abc"}'
    headers = sign_slack_request(body, SECRET)
    verify_slack_signature(
        body,
        headers["X-Slack-Request-Timestamp"],
        headers["X-Slack-Signature"],
    )


def test_invalid_signature_raises_401():
    body = b'{"type":"event_callback"}'
    with pytest.raises(HTTPException) as exc:
        verify_slack_signature(body, "1234567890", "v0=bad")
    assert exc.value.status_code == 401
