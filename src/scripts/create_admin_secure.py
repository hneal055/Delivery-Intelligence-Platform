"""
Secure admin creation. Reads credentials from environment variables --
never hardcode. Usage (PowerShell):

  $env:ADMIN_USERNAME="ops_admin"
  $env:ADMIN_EMAIL="admin@yourdomain.com"
  $env:ADMIN_PASSWORD="a-long-unique-password"
  python src/scripts/create_admin_secure.py

On Railway: set the three variables on the service, then
  railway run python src/scripts/create_admin_secure.py
"""
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import User
from sqlalchemy import select

WEAK_PASSWORDS = {
    "adminpassword123",
    "password",
    "password123",
    "changeme",
    "admin",
}


async def main() -> None:
    username = os.getenv("ADMIN_USERNAME", "").strip()
    email = os.getenv("ADMIN_EMAIL", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")

    if not username or not email or not password:
        sys.exit(
            "Set ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD "
            "environment variables first."
        )
    if len(password) < 12 or password.lower() in WEAK_PASSWORDS:
        sys.exit("ADMIN_PASSWORD must be 12+ characters and not a known weak value.")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        if result.scalars().first():
            print("User '{0}' already exists. Nothing done.".format(username))
            return

        user_in = UserCreate(
            username=username,
            email=email,
            password=password,
            role=UserRole.ADMIN,
        )
        await create_user(db, user_in, UserRole.ADMIN)
        print("Admin '{0}' created.".format(username))


if __name__ == "__main__":
    asyncio.run(main())
