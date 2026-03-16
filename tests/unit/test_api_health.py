"""
HTTP-level tests for public/lightly-authenticated endpoints.
These run against the FastAPI app with DB overridden to an in-memory SQLite.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "online"}


@pytest.mark.asyncio
async def test_root_redirects_to_docs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")
    assert response.status_code in (301, 302, 307, 308)
    assert "/docs" in response.headers.get("location", "")


class TestSecurePing:
    @pytest.mark.asyncio
    async def test_secure_ping_no_token_returns_403(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/secure-ping")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_secure_ping_wrong_token_returns_403(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/secure-ping", headers={"X-DIAD-Token": "wrong-token"})
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_secure_ping_correct_token_returns_200(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/secure-ping", headers={"X-DIAD-Token": "dev-secret-key-123"})
        assert response.status_code == 200
        assert response.json() == {"msg": "Device Authenticated"}


class TestCORSHeaders:
    @pytest.mark.asyncio
    async def test_cors_preflight_from_allowed_origin(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
        # Expect 200 or 204 with CORS headers present
        assert response.status_code in (200, 204)
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_cors_preflight_from_unknown_origin_blocked(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.options(
                "/health",
                headers={
                    "Origin": "http://evil.example.com",
                    "Access-Control-Request-Method": "GET",
                },
            )
        # CORS spec: unknown origin should NOT get allow-origin header
        assert "http://evil.example.com" not in response.headers.get("access-control-allow-origin", "")
