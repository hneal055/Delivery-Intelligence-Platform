import asyncio
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User, Driver
from src.backend.utils.security import get_password_hash
from sqlalchemy.future import select

# Must match fleet_sim.py: f"D{i+1:03d}" with --drivers 20
SIMULATED_DRIVER_IDS = [f"D{i+1:03d}" for i in range(20)]

async def seed_users():
    print("Seeding initial users...")
    async with AsyncSessionLocal() as db:
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

async def seed_drivers():
    print("Seeding simulator driver records...")
    async with AsyncSessionLocal() as db:
        for driver_id in SIMULATED_DRIVER_IDS:
            result = await db.execute(select(Driver).where(Driver.id == driver_id))
            existing = result.scalars().first()
            if not existing:
                db.add(Driver(
                    id=driver_id,
                    name=f"Simulated Driver {driver_id}",
                    status="active",
                ))
                print(f"  Created driver record: {driver_id}")
        await db.commit()
    print(f"Driver seeding complete ({len(SIMULATED_DRIVER_IDS)} drivers ensured).")

async def main():
    await seed_users()
    await seed_drivers()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
