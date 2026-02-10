import asyncio
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User
from src.backend.utils.security import get_password_hash
from sqlalchemy.future import select

async def seed_users():
    print("Seeding initial users...")
    async with AsyncSessionLocal() as db:
        # Check for driver1
        result = await db.execute(select(User).where(User.username == "driver1"))
        user = result.scalars().first()
        
        if not user:
            print("Creating user: driver1")
            new_user = User(
                username="driver1",
                hashed_password=get_password_hash("driverpassword"),
                role="driver",
                is_active=True
            )
            db.add(new_user)
            await db.commit()
            print("User driver1 created successfully.")
        else:
            print("User driver1 already exists.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_users())

