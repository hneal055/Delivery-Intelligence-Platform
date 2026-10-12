"""Staff logins from the internet need the Cloudflare Access email code."""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwk, jwt
from starlette.requests import Request as StarletteRequest

from src.backend.api.routes.auth import login_for_access_token
from src.backend.core.config import settings
from src.backend.services import cf_access

TEAM = "team-test.cloudflareaccess.com"
AUD = "aud-dashboard"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
PUBLIC_PEM = _key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()
PUBLIC_JWK = {**jwk.construct(PUBLIC_PEM, "RS256").to_dict(), "kid": "k1"}


def access_token(aud=AUD, iss=f"https://{TEAM}", exp_in=3600, email="owner@example.com"):
    now = int(time.time())
    return jwt.encode(
        {"aud": [aud], "iss": iss, "email": email, "iat": now, "exp": now + exp_in, "sub": "u1"},
        PRIVATE_PEM, algorithm="RS256", headers={"kid": "k1"},
    )


_ips = iter(range(1, 60000))


def request(internet=True, cookie=None, header=None):
    # A fresh client address per request keeps clear of the login rate limit
    n = next(_ips)
    headers = []
    if internet:
        headers.append((b"cf-connecting-ip", b"203.0.113.9"))
    if cookie:
        headers.append((b"cookie", f"CF_Authorization={cookie}".encode()))
    if header:
        headers.append((b"cf-access-jwt-assertion", header.encode()))
    return StarletteRequest(scope={
        "type": "http", "method": "POST", "path": "/auth/token",
        "query_string": b"", "headers": headers, "client": (f"10.77.{n // 250}.{n % 250 + 1}", 9000),
    })


@pytest.fixture(autouse=True)
def access_on(monkeypatch):
    monkeypatch.setattr(settings, "CF_ACCESS_TEAM_DOMAIN", TEAM)
    monkeypatch.setattr(settings, "CF_ACCESS_AUD", AUD)
    monkeypatch.setattr(cf_access, "_signing_keys", AsyncMock(return_value={"keys": [PUBLIC_JWK]}))


# --- token check ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_cookie_gives_email():
    assert await cf_access.verified_email(request(cookie=access_token())) == "owner@example.com"


@pytest.mark.asyncio
async def test_valid_header_gives_email():
    assert await cf_access.verified_email(request(header=access_token())) == "owner@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [
    access_token(aud="some-other-app"),
    access_token(iss="https://evil.cloudflareaccess.com"),
    access_token(exp_in=-60),
    "not-a-jwt",
])
async def test_bad_tokens_rejected(token):
    assert await cf_access.verified_email(request(cookie=token)) is None


@pytest.mark.asyncio
async def test_no_token_rejected():
    assert await cf_access.verified_email(request()) is None


def test_required_only_from_internet_and_when_configured(monkeypatch):
    assert cf_access.required(request(internet=True))
    assert not cf_access.required(request(internet=False))
    monkeypatch.setattr(settings, "CF_ACCESS_AUD", "")
    assert not cf_access.required(request(internet=True))


# --- login -----------------------------------------------------------------------

def sql_user(role):
    u = MagicMock()
    u.username = "someone"
    u.role = role
    u.hashed_password = "hashed"
    return u


def form(password="pw"):
    f = MagicMock()
    f.username = "someone"
    f.password = password
    return f


async def login(role, req, password_ok=True):
    with patch("src.backend.api.routes.auth.get_user_by_username", AsyncMock(return_value=sql_user(role))), \
         patch("src.backend.api.routes.auth.verify_password", return_value=password_ok) as verify, \
         patch("src.backend.api.routes.auth.ensure_driver_profile", AsyncMock()):
        try:
            return await login_for_access_token(request=req, form_data=form(), db=AsyncMock()), verify
        except HTTPException as exc:
            return exc, verify


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["dispatcher", "manager", "admin"])
async def test_staff_from_internet_without_code_refused_before_password(role):
    result, verify = await login(role, request())
    assert isinstance(result, HTTPException) and result.status_code == 403
    assert "email code" in result.detail
    verify.assert_not_called()  # never reveals whether the password was right


@pytest.mark.asyncio
async def test_staff_from_internet_with_code_logs_in():
    result, _ = await login("dispatcher", request(cookie=access_token()))
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_staff_on_office_pc_needs_no_code():
    result, _ = await login("admin", request(internet=False))
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_driver_from_internet_needs_no_code():
    result, _ = await login("driver", request())
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_check_off_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "CF_ACCESS_TEAM_DOMAIN", "")
    result, _ = await login("dispatcher", request())
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_wrong_password_with_code_still_401():
    result, _ = await login("dispatcher", request(cookie=access_token()), password_ok=False)
    assert isinstance(result, HTTPException) and result.status_code == 401
