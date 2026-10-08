"""
Seed a local development database with login accounts and driver profiles.

Creates (if missing):
  - admin                       password: INITIAL_ADMIN_PASSWORD
  - dispatcher1                 password: INITIAL_DISPATCHER_PASSWORD (skipped if unset)
  - drivers D001..D<count>      password: INITIAL_DRIVER_PASSWORD
    each with a matching Driver profile, used by tools/simulators/fleet_sim.py

Existing accounts are left untouched, including their passwords.
Run `.\\setup_secrets.ps1` once to create .env.backend with these variables.

Usage:  python -m tools.seed_dev_data [--drivers 50]   (from the repo root)
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from src.backend.core.config import settings
from src.backend.core.database import AsyncSessionLocal
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import Driver
from src.backend.services.user_service import create_user, get_user_by_username

CHICAGO = (41.8781, -87.6298)


async def ensure_user(session, username, password, email, role):
    if await get_user_by_username(session, username):
        return False
    await create_user(
        session,
        UserCreate(username=username, email=email, password=password),
        role=role,
    )
    return True


async def seed(driver_count: int):
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
    driver_password = os.getenv("INITIAL_DRIVER_PASSWORD")
    dispatcher_password = os.getenv("INITIAL_DISPATCHER_PASSWORD")

    if not admin_password or not driver_password:
        sys.exit(
            "ERROR: INITIAL_ADMIN_PASSWORD and INITIAL_DRIVER_PASSWORD must be set. "
            "Run .\\setup_secrets.ps1 to create .env.backend."
        )

    async with AsyncSessionLocal() as session:
        if await ensure_user(session, "admin", admin_password, "admin@diplatform.com", UserRole.ADMIN):
            print("Created user: admin")

        if dispatcher_password:
            if await ensure_user(
                session, "dispatcher1", dispatcher_password,
                "dispatcher1@diplatform.com", UserRole.DISPATCHER,
            ):
                print("Created user: dispatcher1")
        else:
            print("INITIAL_DISPATCHER_PASSWORD not set; skipping dispatcher1.")

        created = 0
        for i in range(1, driver_count + 1):
            driver_id = f"D{i:03d}"

            existing = await session.execute(select(Driver).where(Driver.id == driver_id))
            if not existing.scalars().first():
                session.add(Driver(
                    id=driver_id,
                    name=f"Driver {i}",
                    status="active",
                    current_lat=CHICAGO[0],
                    current_lon=CHICAGO[1],
                ))
                await session.commit()

            if await ensure_user(
                session, driver_id, driver_password,
                f"{driver_id.lower()}@diplatform.com", UserRole.DRIVER,
            ):
                created += 1

        print(f"Drivers D001-D{driver_count:03d} ready ({created} new accounts).")


if __name__ == "__main__":
    if settings.IS_PRODUCTION:
        sys.exit("ERROR: refusing to seed development data with ENVIRONMENT=production.")

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--drivers", type=int, default=50)
    asyncio.run(seed(parser.parse_args().drivers))
