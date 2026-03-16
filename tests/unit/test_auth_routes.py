"""
Unit tests for auth route endpoint functions called directly,
bypassing FastAPI routing so Depends() injections are not enforced.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest

from src.backend.api.routes.auth import (
    login_for_access_token,
    refresh_access_token,
    read_users_me,
    RegisterDeviceRequest,
    register_device,
)
from src.backend.models.domain import User, UserRole, Token

_SCOPE = {
    "type": "http", "method": "POST", "path": "/auth/token",
    "query_string": b"", "headers": [], "client": ("10.0.0.1", 9000),
}


def _req():
    return StarletteRequest(scope=dict(_SCOPE))


def _fake_sql_user(username="alice", role="driver"):
    u = MagicMock()
    u.username = username
    u.role = role
    u.hashed_password = "hashed_pw"
    return u


def _fake_form(username="alice", password="password123"):
    f = MagicMock()
    f.username = username
    f.password = password
    return f


def _fake_domain_user(username="alice", role=UserRole.DRIVER):
    return User(
        id="uuid-001", username=username, email=f"{username}@test.com",
        role=role, is_active=True,
    )


# ─── POST /auth/token ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success_returns_token():
    mock_db = AsyncMock()
    with patch("src.backend.api.routes.auth.get_user_by_username", AsyncMock(return_value=_fake_sql_user())), \
         patch("src.backend.api.routes.auth.verify_password", return_value=True):
        result = await login_for_access_token(
            request=_req(), form_data=_fake_form(), db=mock_db,
        )
    assert result["token_type"] == "bearer"
    assert len(result["access_token"]) > 10


@pytest.mark.asyncio
async def test_login_wrong_password_raises_401():
    mock_db = AsyncMock()
    with patch("src.backend.api.routes.auth.get_user_by_username", AsyncMock(return_value=_fake_sql_user())), \
         patch("src.backend.api.routes.auth.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(
                request=_req(), form_data=_fake_form(), db=mock_db,
            )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found_raises_401():
    mock_db = AsyncMock()
    with patch("src.backend.api.routes.auth.get_user_by_username", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await login_for_access_token(
                request=_req(), form_data=_fake_form(), db=mock_db,
            )
    assert exc_info.value.status_code == 401


# ─── POST /auth/token/refresh ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_token_returns_new_token():
    current_user = _fake_domain_user()
    result = await refresh_access_token(request=_req(), current_user=current_user)
    assert result["token_type"] == "bearer"
    assert len(result["access_token"]) > 10


# ─── GET /auth/users/me ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_users_me_returns_current_user():
    user = _fake_domain_user(username="bob", role=UserRole.MANAGER)
    result = await read_users_me(current_user=user)
    assert result.username == "bob"
    assert result.role == UserRole.MANAGER


# ─── POST /auth/register-device ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_device_upserts_token():
    mock_db = AsyncMock()
    # Simulate no existing token found
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    current_user = _fake_domain_user()
    body = RegisterDeviceRequest(token="device-token-abc", platform="android")

    result = await register_device(request=_req(), body=body, current_user=current_user, db=mock_db)
    assert result["status"] == "registered"
    mock_db.commit.assert_awaited()
