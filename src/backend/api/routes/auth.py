from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.backend.models.domain import Token, User
from src.backend.utils.security import verify_password, create_access_token
from src.backend.services.user_service import get_user_by_username
from src.backend.api.deps import get_current_active_user
from src.backend.api.limiter import limiter
from src.backend.core.config import settings
from src.backend.core.database import get_db
from src.backend.models.sql_models import DeviceToken

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

    if not user_sql or not verify_password(form_data.password, user_sql.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
