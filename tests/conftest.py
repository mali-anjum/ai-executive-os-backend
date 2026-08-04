import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(autouse=True)
def bypass_user_db_sync(monkeypatch):
    async def noop(db, auth):
        return None

    monkeypatch.setattr("app.core.security.ensure_user_row", noop)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
