import ssl

from app.core.redis_client import _normalize_redis_url


def test_normalize_rediss_url_moves_ssl_cert_reqs_to_kwargs():
    url = "rediss://default:secret@host.upstash.io:6379?ssl_cert_reqs=CERT_NONE"
    clean_url, kwargs = _normalize_redis_url(url)
    assert clean_url == "rediss://default:secret@host.upstash.io:6379"
    assert kwargs == {"ssl_cert_reqs": ssl.CERT_NONE}


def test_normalize_redis_url_unchanged():
    url = "redis://localhost:6379/0"
    clean_url, kwargs = _normalize_redis_url(url)
    assert clean_url == url
    assert kwargs == {}
