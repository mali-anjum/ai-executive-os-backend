"""
Cryptographic trust boundary for POST /webhook/slack.

Verifies X-Slack-Signature + timestamp before dedupe or Celery — rejects forged
payloads. Required in production; skipped only when SLACK_SIGNING_SECRET is empty.
"""

import hashlib
import hmac
import time

from fastapi import HTTPException, status

from app.core.config import settings


def verify_slack_signature(
    body: bytes,
    timestamp: str | None,
    signature: str | None,
) -> None:
    secret = settings.slack_signing_secret
    if not secret:
        return

    if not timestamp or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Slack signature headers",
        )

    if abs(time.time() - int(timestamp)) > settings.slack_webhook_max_age_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Stale Slack request timestamp",
        )

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = (
        "v0="
        + hmac.new(
            secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(computed, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature",
        )
