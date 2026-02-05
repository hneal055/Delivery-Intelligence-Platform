from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.domain import Token, User
from src.backend.utils.security import verify_password, create_access_token
from src.backend.services.user_service import get_user_by_username
from src.backend.api.deps import get_current_active_user
from src.backend.core.config import settings
from src.backend.core.database import get_db

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Note: OAuth2PasswordRequestForm expects "username" and "password" fields
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
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user
