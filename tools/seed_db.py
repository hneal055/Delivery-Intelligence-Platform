import asyncio
import sys
import os
from sqlalchemy import select

# Add project root to Python path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user, get_user_by_username
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import Driver

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("Checking for existing users and drivers...")
        
        # Create pool of drivers for load testing (1 to 50)
        for i in range(1, 51):
            username = f"driver{i}"
            driver_id = f"D{i:03d}" # D001, D002...
            
            # 1. Create User
            if not await get_user_by_username(session, username):
                # print(f"Creating {username}...")
                await create_user(
                    session,
                    UserCreate(username=username, email=f"{username}@example.com", password="driverpassword", role=UserRole.DRIVER),
                    role=UserRole.DRIVER
                )

            # 2. Create Driver Profile (Explicit IDs for Simulator)
            # The simulator uses D001, D002... so we must seed these exactly.
            result = await session.execute(select(Driver).where(Driver.id == driver_id))
            if not result.scalars().first():
                # print(f"Creating Driver Profile {driver_id}...")
                new_driver = Driver(
                    id=driver_id,
                    name=f"Driver {i}",
                    status="active",
                    vehicle_id=f"V-{i:03d}",
                    current_lat=41.8781, # Default Chicago
                    current_lon=-87.6298
                )
                session.add(new_driver)
        
        # 3. Create Admin User
        if not await get_user_by_username(session, "admin"):
            print("Creating admin user...")
            await create_user(
                session,
                UserCreate(username="admin", email="admin@example.com", password="adminpassword", role=UserRole.ADMIN),
                role=UserRole.ADMIN
            )

        await session.commit()
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    if "DATABASE_URL" not in os.environ:
         # Default to localhost port 5433 for external access if running locally
         os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/delivery_db"
            
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Seeding failed: {e}")
