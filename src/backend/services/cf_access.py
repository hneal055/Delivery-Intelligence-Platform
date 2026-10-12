"""
Cloudflare Access proof for staff logins that come from the internet.

The dashboard sits behind Cloudflare Access (an emailed one-time code). The
/api path must stay open for the driver phones, so on its own Access does
not stop someone posting a password straight to /api/auth/token. After a
browser passes the code screen, Cloudflare gives it a signed token (the
CF_Authorization cookie), which the browser also sends with its /api calls.
Staff logins arriving through the tunnel must carry a valid one.

Requests that did not come through Cloudflare (this PC, the office network)
carry no CF-Connecting-IP header and are not affected, so there is always a
way in locally. With CF_ACCESS_TEAM_DOMAIN / CF_ACCESS_AUD unset, the check
is off.
"""
import logging
import time
from typing import Optional

import httpx
from fastapi import Request
from jose import JWTError, jwt

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

CERTS_TTL_SECONDS = 3600
_certs: dict = {"jwks": None, "fetched": 0.0}


def enabled() -> bool:
    return bool(settings.CF_ACCESS_TEAM_DOMAIN and settings.CF_ACCESS_AUD)


def from_internet(request: Request) -> bool:
    """Cloudflare adds CF-Connecting-IP to every request it forwards."""
    return bool(request.headers.get("cf-connecting-ip"))


def required(request: Request) -> bool:
    return enabled() and from_internet(request)


def _team_url() -> str:
    domain = settings.CF_ACCESS_TEAM_DOMAIN.strip().rstrip("/")
    return domain if domain.startswith("https://") else f"https://{domain}"


async def _signing_keys(refresh: bool = False) -> dict:
    """Cloudflare's public signing keys for this team, cached for an hour."""
    if refresh or _certs["jwks"] is None or time.time() - _certs["fetched"] > CERTS_TTL_SECONDS:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{_team_url()}/cdn-cgi/access/certs")
            response.raise_for_status()
        _certs["jwks"] = response.json()
        _certs["fetched"] = time.time()
    return _certs["jwks"]


async def verified_email(request: Request) -> Optional[str]:
    """Email from a valid Cloudflare Access token on the request, else None."""
    token = request.headers.get("cf-access-jwt-assertion") or request.cookies.get("CF_Authorization")
    if not token:
        return None
    audiences = [a.strip() for a in settings.CF_ACCESS_AUD.split(",") if a.strip()]
    # Second pass refreshes the keys, in case Cloudflare rotated them.
    for refresh in (False, True):
        try:
            jwks = await _signing_keys(refresh=refresh)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Could not fetch Cloudflare Access keys: %s", exc)
            return None
        for audience in audiences:
            try:
                claims = jwt.decode(
                    token, jwks, algorithms=["RS256"], audience=audience, issuer=_team_url()
                )
                return claims.get("email") or claims.get("sub") or "unknown"
            except JWTError:
                continue
    return None
