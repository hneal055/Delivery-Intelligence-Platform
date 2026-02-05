import asyncio
import sys
import os

# Add project root to Python path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user, get_user_by_username
from src.backend.models.domain import UserCreate, UserRole

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("Checking for existing users...")
        
        # 1. Create Driver Users (for Simulator)
        # Create standard 'driver1' used by simple checks
        if not await get_user_by_username(session, "driver1"):
            print("Creating driver1...")
            await create_user(
                session, 
                UserCreate(username="driver1", email="driver1@example.com", password="driverpassword", role=UserRole.DRIVER),
                role=UserRole.DRIVER
            )
        
        # Create pool of drivers for load testing
        for i in range(2, 51):
            username = f"driver{i}"
            if not await get_user_by_username(session, username):
                # print(f"Creating {username}...")
                await create_user(
                    session,
                    UserCreate(username=username, email=f"{username}@example.com", password="driverpassword", role=UserRole.DRIVER),
                    role=UserRole.DRIVER
                )
        
        # 2. Create Admin User
        if not await get_user_by_username(session, "admin"):
            print("Creating admin user...")
            await create_user(
                session,
                UserCreate(username="admin", email="admin@example.com", password="adminpassword", role=UserRole.ADMIN),
                role=UserRole.ADMIN
            )
            
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    # Ensure we point to the HOST exposed port (5433) for this script
    # The default config points to localhost:5432, but our docker-compose maps 5433->5432
    if "DATABASE_URL" not in os.environ:
         os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/delivery_db"
            
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Seeding failed: {e}")
