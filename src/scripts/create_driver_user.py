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

async def create_driver():
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.username == "driver1"))
        existing = result.scalars().first()
        
        if existing:
            print("Driver user already exists.")
            return

        user_in = UserCreate(
            username="driver1",
            email="driver1@example.com", 
            password="driverpassword",
            role=UserRole.DRIVER
        )
        
        await create_user(db, user_in, UserRole.DRIVER)
        print("Driver user (driver1) created successfully.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(create_driver())
    finally:
        loop.close()

