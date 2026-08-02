from fastapi import APIRouter
from src.backend.core.config import settings

router = APIRouter(
    prefix="/oidc",
    tags=["OIDC"]
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
        )
    }


@router.get("/config")
async def oidc_config():
    """
    Return public OIDC configuration.
    """

    return {
        "enabled": settings.OIDC_ENABLED,
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID
    }