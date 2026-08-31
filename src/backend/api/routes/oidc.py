import logging
import secrets

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.backend.core.config import settings
from src.backend.core.oidc_client import oauth
from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import (
    get_user_by_username,
    create_user,
)
from src.backend.models.domain import UserCreate, UserRole


logger = logging.getLogger(__name__)

# Entra email -> role. Everything else falls through to DRIVER.
ROLE_BY_EMAIL = {
    "howard@scenereaderstudio.com": UserRole.ADMIN,
    "dispatcher@scenereaderstudio.com": UserRole.DISPATCHER,
    "manager@scenereaderstudio.com": UserRole.MANAGER,
}

# Entra may present the address under any of these claims depending on
# account type (tenant member vs guest vs personal MSA).
EMAIL_CLAIMS = ("preferred_username", "email", "upn", "unique_name")


router = APIRouter(
    prefix="/oidc",
    tags=["OIDC"],
)


def require_admin(request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    return user


@router.get("/health")
async def oidc_health():
    return {
        "enabled": settings.OIDC_ENABLED,
        "configured": bool(
            settings.OIDC_ISSUER_URL
            and settings.OIDC_CLIENT_ID
        ),
    }


@router.get("/config")
async def oidc_config():
    return {
        "enabled": settings.OIDC_ENABLED,
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID,
    }


@router.get("/login")
async def oidc_login(request: Request):

    if not settings.OIDC_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="OIDC authentication is disabled",
        )

    return await oauth.microsoft.authorize_redirect(
        request,
        settings.OIDC_REDIRECT_URI,
    )


@router.get("/callback")
async def oidc_callback(request: Request):

    # A failed/abandoned consent, an expired login, or a session cookie that
    # did not survive the round trip (e.g. starting on 127.0.0.1 and returning
    # on localhost) all surface here. Report them instead of a bare 500.
    try:
        token = await oauth.microsoft.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("Entra authorization failed: %s", exc.error)
        raise HTTPException(
            status_code=400,
            detail=f"Entra sign-in failed: {exc.error}. Please retry from /oidc/login.",
        )

    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(
            status_code=502,
            detail="User information not returned by Entra",
        )

    email = next(
        (userinfo[claim] for claim in EMAIL_CLAIMS if userinfo.get(claim)),
        None,
    )
    name = userinfo.get("name") or email

    if not email:
        logger.error(
            "No email claim in Entra userinfo; claims present: %s",
            sorted(userinfo.keys()),
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "Entra returned no email address. Checked claims: "
                + ", ".join(EMAIL_CLAIMS)
            ),
        )

    email = email.lower()
    user_role = ROLE_BY_EMAIL.get(email, UserRole.DRIVER)

    async with AsyncSessionLocal() as db:

        user = await get_user_by_username(
            db,
            email,
        )

        if not user:

            user = await create_user(
                db,
                UserCreate(
                    username=email,
                    email=email,
                    password=secrets.token_urlsafe(32),
                ),
                role=user_role,
            )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="This account is disabled.",
        )

    session_role = user.role

    request.session["user"] = {
        "email": email,
        "name": name,
        "role": session_role.upper(),
    }

    return RedirectResponse(
        url="/oidc/dashboard",
        status_code=302,
    )


@router.get("/me")
async def current_user(request: Request):

    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    return user


@router.get("/dashboard")
async def dashboard(request: Request):

    message = request.query_params.get("message")
    user = request.session.get("user")

    if not user:
        return {
            "message": message or "Not authenticated"
        }

    return {
        "message": message or "Welcome to Delivery Intelligence Platform",
        "user": user,
    }


@router.get("/admin")
async def admin_panel(request: Request):

    user = require_admin(request)

    return {
        "message": "Administration Area",
        "user": user,
    }


@router.get("/logout")
async def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        url="/oidc/dashboard?message=You+have+been+logged+out",
        status_code=302,
    )