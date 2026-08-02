from fastapi import APIRouter, HTTPException

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
async def oidc_login():
    """
    Placeholder Microsoft Entra ID login endpoint.
    """

    if not settings.OIDC_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="OIDC authentication is disabled",
        )

    return {
        "message": "OIDC login endpoint ready",
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
    }


@router.get("/callback")
async def oidc_callback():
    """
    Placeholder callback endpoint for OIDC authorization flow.
    """

    return {
        "message": "OIDC callback endpoint reached",
    }