import asyncio
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import User
from sqlalchemy import select

async def create_admin():
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.username == "admin_user"))
        existing = result.scalars().first()
        
        if existing:
            print("Admin user already exists.")
            return

        user_in = UserCreate(
            username="admin_user",
            email="admin@example.com", 
            password="adminpassword123",
            role=UserRole.ADMIN
        )
        
        await create_user(db, user_in, UserRole.ADMIN)
        print("Admin user created successfully.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_admin())
