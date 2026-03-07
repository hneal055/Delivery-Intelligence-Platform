import asyncio
import sys
import os
from sqlalchemy import select, text

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default DATABASE_URL for local dev (override via env var for Docker)
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/delivery_db"

from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import create_user, get_user_by_username
from src.backend.models.domain import UserCreate, UserRole

# -----------------------------------------------------------------------
# Fleet size constants
#   FLEET_SMALL  = simulator fleet_sim.py --drivers 20 (D001-D020)
#   FLEET_LARGE  = full load-test pool                 (D001-D050)
# Seeding FLEET_LARGE covers both ranges.
# -----------------------------------------------------------------------
FLEET_SMALL = 20
FLEET_LARGE = 50

SYSTEM_ACCOUNTS = [
    {"username": "admin",       "password": "adminpassword",      "email": "admin@diplatform.com",       "role": UserRole.ADMIN},
    {"username": "dispatcher1", "password": "dispatcherpassword",  "email": "dispatcher1@diplatform.com", "role": UserRole.MANAGER},
]


async def seed():
    async with AsyncSessionLocal() as db:
        created_users = 0
        created_profiles = 0

        # ── System accounts (admin, dispatcher) ──────────────────────────
        for acct in SYSTEM_ACCOUNTS:
            if not await get_user_by_username(db, acct["username"]):
                await create_user(
                    db,
                    UserCreate(username=acct["username"], email=acct["email"], password=acct["password"]),
                    role=acct["role"],
                )
                created_users += 1
                print(f"  [+] user    : {acct['username']} ({acct['role'].value})")

        # ── Driver accounts + profiles (D001-D050, covers 20-driver fleet) ─
        # Raw SQL is used for driver profiles to avoid ORM model/column
        # mismatches between environments (e.g. PostGIS column optional locally).
        for i in range(1, FLEET_LARGE + 1):
            username  = f"driver{i}"
            driver_id = f"D{i:03d}"

            # User account
            if not await get_user_by_username(db, username):
                await create_user(
                    db,
                    UserCreate(username=username, email=f"{username}@diplatform.com", password="driverpassword"),
                    role=UserRole.DRIVER,
                )
                created_users += 1

            # Driver profile — raw SQL so it works with or without PostGIS
            chk = await db.execute(text("SELECT 1 FROM drivers WHERE id = :id"), {"id": driver_id})
            if not chk.scalar():
                await db.execute(
                    text(
                        "INSERT INTO drivers (id, name, status, vehicle_id, current_lat, current_lon, last_updated) "
                        "VALUES (:id, :name, 'active', :vid, :lat, :lon, NOW()) "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {"id": driver_id, "name": f"Driver {i}", "vid": f"V-{i:03d}",
                     "lat": 41.8781, "lon": -87.6298},
                )
                created_profiles += 1

        await db.commit()

        print(f"\nSeeding complete.")
        print(f"  Users created   : {created_users}")
        print(f"  Profiles created: {created_profiles}")
        print(f"  Fleet coverage  : D001-D{FLEET_LARGE:03d}  ({FLEET_LARGE} drivers total, includes {FLEET_SMALL}-driver sim range)")


if __name__ == "__main__":
    asyncio.run(seed())
