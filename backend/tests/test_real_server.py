import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_vpn_health_and_root_are_available():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        health = await ac.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        root = await ac.get("/")
        assert root.status_code == 200
        assert root.json() == {"message": "VPN Project API is running"}
