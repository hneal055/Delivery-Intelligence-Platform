from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from src.backend.core.config import settings
from src.backend.models.domain import TokenData, User
from src.backend.services.user_service import get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    # In a real app we might verify if user exists in DB here
    # user = get_user_by_username(username)
    # if user is None:
    #     raise credentials_exception
    return token_data

async def get_current_active_user(
    current_user: Annotated[TokenData, Depends(get_current_user)]
):
    # logic for active user...
    return current_user

