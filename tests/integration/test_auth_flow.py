"""
Integration tests: Auth flow
- POST /auth/token  → success, bad-password, unknown-user
- POST /auth/token/refresh → success with valid token
- GET  /auth/users/me → identity of authenticated user
- POST /auth/register-device → device token upsert
"""
import pytest
from tests.integration.conftest import int_db_seed_user
from src.backend.models.domain import UserRole


@pytest.mark.asyncio
async def test_login_success(int_client_anon):
    """Valid credentials return an access token."""
    client, db = int_client_anon
    await int_db_seed_user(db, "login_user", "Correct1!", UserRole.DRIVER)

    resp = await client.post("/auth/token", data={
        "username": "login_user",
        "password": "Correct1!",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(int_client_anon):
    """Wrong password returns 401."""
    client, db = int_client_anon
    await int_db_seed_user(db, "pw_user", "RightPass1!", UserRole.DRIVER)

    resp = await client.post("/auth/token", data={
        "username": "pw_user",
        "password": "WrongPass!",
    })
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_user(int_client_anon):
    """Non-existent user returns 401."""
    client, db = int_client_anon

    resp = await client.post("/auth/token", data={
        "username": "ghost_user",
        "password": "AnyPass1!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(int_client_manager):
    """Authenticated user can refresh token."""
    client, db, mgr = int_client_manager

    resp = await client.post("/auth/token/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body


@pytest.mark.asyncio
async def test_users_me_returns_current_user(int_client_manager):
    """GET /auth/users/me returns the authenticated user's identity."""
    client, db, mgr = int_client_manager

    resp = await client.get("/auth/users/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "int_manager"
    assert body["role"] == UserRole.MANAGER.value


@pytest.mark.asyncio
async def test_register_device_success(int_client_driver):
    """POST /auth/register-device stores a push token."""
    client, db, drv = int_client_driver

    resp = await client.post("/auth/register-device", json={
        "token": "fcm-device-token-abc123",
        "platform": "android",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "registered"


@pytest.mark.asyncio
async def test_register_device_upsert(int_client_driver):
    """Registering the same token twice does not raise a conflict."""
    client, db, drv = int_client_driver
    payload = {"token": "same-token-xyz", "platform": "ios"}

    resp1 = await client.post("/auth/register-device", json=payload)
    resp2 = await client.post("/auth/register-device", json=payload)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
