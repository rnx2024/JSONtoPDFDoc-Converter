import pytest
from httpx import ASGITransport, AsyncClient

import auth
from main import app

TEST_API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _set_test_api_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", TEST_API_KEY)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
