from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.models.sql_models import User as UserSQL
from src.backend.models.domain import UserCreate, UserRole
from src.backend.utils.security import get_password_hash


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserSQL]:
    """Retrieve a user by their unique username."""
    result = await db.execute(select(UserSQL).where(UserSQL.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserSQL]:
    """Retrieve a user by their email address."""
    result = await db.execute(select(UserSQL).where(UserSQL.email == email))
    return result.scalars().first()


async def create_user(
    db: AsyncSession,
    user_in: UserCreate,
    role: UserRole = UserRole.DRIVER,
) -> UserSQL:
    """Create a new user with a hashed password."""
    hashed_password = get_password_hash(user_in.password)
    db_user = UserSQL(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        role=role.value if hasattr(role, "value") else str(role),
        is_active=True,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user