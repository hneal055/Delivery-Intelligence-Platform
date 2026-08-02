from fastapi import APIRouter, HTTPException, Request
from src.backend.core.oidc_client import oauth
from src.backend.core.config import settings

router = APIRouter(
    prefix="/oidc",
    tags=["OIDC"],
)


@router.get("/health")
async def oidc_health():
    """
    Health endpoint for OIDC subsystem.
    """

    return {
        "enabled": settings.OIDC_ENABLED,
        "configured": bool(
            settings.OIDC_ISSUER_URL
            and settings.OIDC_CLIENT_ID
        ),
    }


@router.get("/config")
async def oidc_config():
    """
    Return public OIDC configuration.
    """

    return {
        "enabled": settings.OIDC_ENABLED,
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID,
    }


@router.get("/login")
async def oidc_login(request: Request):
    """
    Redirect user to Microsoft Entra ID login.
    """

    if not settings.OIDC_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="OIDC authentication is disabled",
        )

    return await oauth.microsoft.authorize_redirect(
        request,
        settings.OIDC_REDIRECT_URI,
    
 