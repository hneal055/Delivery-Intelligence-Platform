import logging
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.backend.models.domain import Token, User, UserRole
from src.backend.utils.security import verify_password, create_access_token
from src.backend.services.user_service import get_user_by_username
from src.backend.api.deps import get_current_active_user
from src.backend.api.limiter import limiter
from src.backend.core.config import settings
from src.backend.core.database import get_db
from src.backend.models.sql_models import DeviceToken
from src.backend.services.driver_profile import ensure_driver_profile
from src.backend.services.heartbeat import heartbeat_service
from src.backend.services import cf_access

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate and return a JWT access token. Rate-limited to 10 attempts/min per IP."""
    user_sql = await get_user_by_username(db, form_data.username)

    # Staff logins from the internet need the dashboard email code first
    # (Cloudflare Access). Checked before the password, so this answer never
    # reveals whether a guessed password was right. Drivers are not affected.
    if (
        user_sql
        and user_sql.role != UserRole.DRIVER.value
        and cf_access.required(request)
        and not await cf_access.verified_email(request)
    ):
        logger.warning("Staff login for %s from the internet without the email code; refused", user_sql.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff sign-in from the internet needs the email code first. "
                   "Reload the dashboard page, enter the code Cloudflare emails you, then sign in.",
        )

    if not user_sql or not verify_password(form_data.password, user_sql.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # A driver who can log in must also be assignable: make sure their
    # driver profile exists, and mark them online.
    if user_sql.role == UserRole.DRIVER.value:
        await ensure_driver_profile(db, user_sql.username)
        await heartbeat_service.update(user_sql.username)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user_sql.username,
        role=user_sql.role,
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token/refresh", response_model=Token)
@limiter.limit("30/minute")
async def refresh_access_token(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Refresh an access token using the current valid token. Rate-limited to 30/min per IP."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=current_user.username,
        role=current_user.role,
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user


class RegisterDeviceRequest(BaseModel):
    token: str
    platform: str = "android"  # android, ios, web


@router.post("/register-device")
@limiter.limit("20/minute")
async def register_device(
    request: Request,
    body: RegisterDeviceRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a device push token for the current user (upsert). Rate-limited to 20/min per IP."""
    await db.execute(delete(DeviceToken).where(DeviceToken.token == body.token))

    device = DeviceToken(
        user_id=current_user.id,
        token=body.token,
        platform=body.platform,
    )
    db.add(device)
    await db.commit()
    return {"status": "registered", "platform": body.platform}


@router.get("/oidc/config")
async def get_oidc_config():
    """Return OIDC configuration for the frontend (public endpoint)."""
    if not settings.OIDC_ENABLED:
        return {"enabled": False}
    return {
        "enabled": True,
        "issuer_url": settings.OIDC_ISSUER_URL,
        "client_id": settings.OIDC_CLIENT_ID,
    }
