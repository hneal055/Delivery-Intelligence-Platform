from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User
from src.backend.models.domain import UserRole


class RoleUpdateRequest(BaseModel):
    role: str


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


def require_admin(request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    return user


@router.get("")
async def get_users(request: Request):

    require_admin(request)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User)
        )

        users = result.scalars().all()

        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            }
            for user in users
        ]


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    request: Request,
):

    require_admin(request)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_update: RoleUpdateRequest,
    request: Request,
):

    require_admin(request)

    valid_roles = {role.value for role in UserRole}

    new_role = role_update.role.lower()

    if new_role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid role. Must be one of: "
                + ", ".join(
                    sorted(role.upper() for role in valid_roles)
                )
            ),
        )

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        user.role = new_role

        await db.commit()
        await db.refresh(user)

        return {
            "message": "Role updated",
            "user_id": user.id,
            "role": user.role,
        }