from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config import settings
from src.backend.models.domain import TokenData, User, UserRole
from src.backend.services.user_service import get_user_by_username
from src.backend.core.database import get_db
from src.backend.core.permissions import Permission, ROLE_PERMISSIONS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    user_sql = await get_user_by_username(db, username=token_data.username)
    if user_sql is None:
        raise credentials_exception

    # Convert to Domain Model
    user = User(
        id=user_sql.id,
        username=user_sql.username,
        email=user_sql.email,
        role=UserRole(user_sql.role),
        is_active=user_sql.is_active,
    )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


async def get_current_dispatcher(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require dispatcher, manager or admin role for dispatch operations."""
    if current_user.role not in (
        UserRole.DISPATCHER,
        UserRole.MANAGER,
        UserRole.ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher (dispatcher/manager/admin) role required",
        )
    return current_user


class PermissionChecker:
    def __init__(self, required_permission: Permission):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(get_current_active_user)) -> User:
        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required: {self.required_permission.value}",
            )
        return user