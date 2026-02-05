from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.backend.models.domain import User as UserDomain, UserCreate, UserRole
from src.backend.models.sql_models import User as UserSQL
from src.backend.utils.security import get_password_hash

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserSQL]:
    result = await db.execute(select(UserSQL).where(UserSQL.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: UserCreate, role: UserRole = UserRole.DRIVER) -> UserDomain:
    hashed_password = get_password_hash(user.password)
    db_user = UserSQL(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role.value,
        is_active=True
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Convert SQL model to Domain model
    return UserDomain(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        role=UserRole(db_user.role),
        is_active=db_user.is_active
    )
