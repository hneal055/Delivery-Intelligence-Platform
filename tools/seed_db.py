import os
import sys
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.core.database import AsyncSessionLocal
from src.backend.models.domain import UserCreate, UserRole
from src.backend.services.user_service import create_user, get_user_by_username

async def seed():
    admin_pass = os.getenv("ADMIN_PASSWORD")
    dispatcher_pass = os.getenv("DISPATCHER_PASSWORD")
    driver_pass = os.getenv("DRIVER_PASSWORD")

    if not admin_pass or not dispatcher_pass or not driver_pass:
        print("ERROR: ADMIN_PASSWORD, DISPATCHER_PASSWORD, and DRIVER_PASSWORD environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        accounts = [
            {"username": "admin", "password": admin_pass, "email": "admin@diplatform.com", "role": UserRole.ADMIN},
            {"username": "dispatcher1", "password": dispatcher_pass, "email": "dispatcher1@diplatform.com", "role": UserRole.DISPATCHER},
        ]

        for acct in accounts:
            existing = await get_user_by_username(session, acct["username"])
            if existing:
                print(f"User {acct['username']} already exists. Skipping.")
                continue
            await create_user(session, UserCreate(username=acct["username"], email=acct["email"], password=acct["password"]), role=acct["role"])
            print(f"Created user: {acct['username']}")

        # Seed drivers
        for i in range(1, 4):
            uname = f"driver{i}"
            existing = await get_user_by_username(session, uname)
            if existing:
                print(f"Driver {uname} already exists. Skipping.")
                continue
            await create_user(session, UserCreate(username=uname, email=f"{uname}@diplatform.com", password=driver_pass), role=UserRole.DRIVER)
            print(f"Created driver: {uname}")

        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())
