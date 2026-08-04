from app.core.db_connect import async_connect_args, resolve_ipv4, sync_connect_args


def test_localhost_has_no_extra_connect_args():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sop_automator"
    assert sync_connect_args(url) == {}
    assert async_connect_args(url) == {}


def test_supabase_direct_may_use_ipv4_hostaddr():
    url = (
        "postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres"
    )
    sync = sync_connect_args(url)
    assert sync.get("sslmode") == "require"
    if resolve_ipv4("db.example.supabase.co"):
        assert "hostaddr" in sync


def test_supabase_pooler_does_not_use_hostaddr():
    url = (
        "postgresql+asyncpg://postgres.abc:secret@"
        "aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"
    )
    sync = sync_connect_args(url)
    assert sync.get("sslmode") == "require"
    assert "hostaddr" not in sync
    assert "hostaddr" not in async_connect_args(url)
