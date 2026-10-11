"""
Driver profiles for driver login accounts.

A driver's ID is their login username. The drivers table is what dispatch
lists and assigns to, so every driver account needs a row there; it is
created the first time the driver logs in (and backfilled by migration
e2f3a4b5c6d7 for accounts that existed before).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.sql_models import Driver


async def ensure_driver_profile(db: AsyncSession, username: str) -> Driver:
    driver = await db.get(Driver, username)
    if driver is None:
        driver = Driver(id=username, name=username, status="active")
        db.add(driver)
        await db.commit()
    return driver
