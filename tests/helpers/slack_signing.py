import hashlib
import hmac
import time


def sign_slack_request(body: bytes, secret: str, timestamp: str | None = None) -> dict[str, str]:
    ts = timestamp or str(int(time.time()))
    basestring = f"v0:{ts}:{body.decode('utf-8')}"
    sig = (
        "v0="
        + hmac.new(secret.encode(), basestring.encode(), hashlib.sha256).hexdigest()
    )
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": sig,
    }
