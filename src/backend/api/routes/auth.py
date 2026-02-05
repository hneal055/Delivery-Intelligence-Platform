from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from src.backend.models.domain import Token, User
from src.backend.utils.security import verify_password, create_access_token
from src.backend.services.user_service import get_user_by_username, fake_users_db
from src.backend.api.deps import get_current_active_user
from src.backend.core.config import settings

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Note: OAuth2PasswordRequestForm expects "username" and "password" fields
    user = get_user_by_username(form_data.username)
    
    # We need to retrieve the hashed password from the DB to verify
    # Since get_user_by_username returns a User model (sanitized), we cheat and peek at the DB for this Phase 1
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db_user_dict = fake_users_db.get(form_data.username)
    if not verify_password(form_data.password, db_user_dict["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, 
        role=user.role.value,
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

