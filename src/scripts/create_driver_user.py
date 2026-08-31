import asyncio
import sys
import os
import secrets

# Add src to path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import User
from sqlalchemy import select

async def create_driver():
    # Safety guard: require explicit env var to allow dev seeding
    if os.getenv("ALLOW_DEV_SEED") != "true":
        print("Refusing to seed driver user: set ALLOW_DEV_SEED=true to enable seeding in dev environments.")
        return

    password = os.getenv("DEV_DRIVER_PASSWORD")
    if not password:
        # Generate a random, single-use password and print it for the operator
        password = secrets.token_urlsafe(12)
        print(f"DEV_DRIVER_PASSWORD not set — generated password for seeding: {password}")

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
            password=password,
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
