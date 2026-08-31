from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.deps import get_db, get_current_active_admin
from src.backend.models.sql_models import User as UserSQL
from src.backend.models.domain import User as UserDomain, UserRole
from src.backend.services.audit_service import write_audit_log


class RoleUpdateRequest(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_admin: UserDomain = Depends(get_current_active_admin),
):
    """List all registered users (Admin only)."""
    result = await db.execute(select(UserSQL))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: UserDomain = Depends(get_current_active_admin),
):
    """Fetch user details by ID (Admin only)."""
    result = await db.execute(select(UserSQL).where(UserSQL.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_update: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: UserDomain = Depends(get_current_active_admin),
):
    """Update a user's role and write an audit log entry."""
    valid_roles = {role.value for role in UserRole}
    new_role = role_update.role.lower()

    if new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid role. Must be one of: "
                + ", ".join(sorted(role.upper() for role in valid_roles))
            ),
        )

    result = await db.execute(select(UserSQL).where(UserSQL.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin self-demotion
    if user.id == current_admin.id and new_role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot remove their own admin role",
        )

    old_role = user.role
    user.role = new_role

    actor_role_str = (
        current_admin.role.value
        if hasattr(current_admin.role, "value")
        else str(current_admin.role)
    )

    await write_audit_log(
        db=db,
        actor_email=current_admin.email,
        actor_role=actor_role_str,
        action="ROLE_CHANGE",
        target_user=user.email,
        details=f"{old_role} -> {user.role}",
    )

    await db.commit()
    await db.refresh(user)

    return {
        "message": "Role updated",
        "user_id": user.id,
        "role": user.role,
    }


@router.put("/{user_id}/enable")
async def enable_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: UserDomain = Depends(get_current_active_admin),
):
    """Enable a deactivated user account."""
    result = await db.execute(select(UserSQL).where(UserSQL.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_active:
        return {
            "message": "User already enabled",
            "user_id": user.id,
            "is_active": user.is_active,
        }

    user.is_active = True

    actor_role_str = (
        current_admin.role.value
        if hasattr(current_admin.role, "value")
        else str(current_admin.role)
    )

    await write_audit_log(
        db=db,
        actor_email=current_admin.email,
        actor_role=actor_role_str,
        action="USER_ENABLED",
        target_user=user.email,
        details="User account enabled",
    )

    await db.commit()
    await db.refresh(user)

    return {
        "message": "User enabled",
        "user_id": user.id,
        "is_active": user.is_active,
    }


@router.put("/{user_id}/disable")
async def disable_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: UserDomain = Depends(get_current_active_admin),
):
    """Disable a user account."""
    result = await db.execute(select(UserSQL).where(UserSQL.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin self-lockout
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot disable their own account",
        )

    if not user.is_active:
        return {
            "message": "User already disabled",
            "user_id": user.id,
            "is_active": user.is_active,
        }

    user.is_active = False

    actor_role_str = (
        current_admin.role.value
        if hasattr(current_admin.role, "value")
        else str(current_admin.role)
    )

    await write_audit_log(
        db=db,
        actor_email=current_admin.email,
        actor_role=actor_role_str,
        action="USER_DISABLED",
        target_user=user.email,
        details="User account disabled",
    )

    await db.commit()
    await db.refresh(user)

    return {
        "message": "User disabled",
        "user_id": user.id,
        "is_active": user.is_active,
    }