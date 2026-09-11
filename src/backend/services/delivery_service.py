from datetime import datetime, timedelta
import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.backend.models.sql_models import Driver, Package
from src.backend.services.heartbeat import heartbeat_service
from src.backend.services.traffic_service import traffic_service

logger = logging.getLogger(__name__)


async def update_driver_location(
    db: AsyncSession,
    driver_id: str,
    lat: float,
    lon: float,
    name: str = None,
):
    """
    Update driver location and record a heartbeat.
    """

    result = await db.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = result.scalars().first()

    if not driver:
        driver = Driver(
            id=driver_id,
            name=name or driver_id,
            status="active",
        )
        db.add(driver)

    driver.current_lat = lat
    driver.current_lon = lon
    driver.last_updated = datetime.utcnow()

    logger.warning(
        "HEARTBEAT UPDATE FOR DRIVER %s",
        driver_id,
    )

    await heartbeat_service.update(driver_id)

    await db.commit()
    await db.refresh(driver)

    return driver


async def update_package_status(
    db: AsyncSession,
    package_id: str,
    status: str,
    driver_id: str,
    dest_lat: float = None,
    dest_lon: float = None,
):
    """
    Update package status and create simulation data
    when packages do not already exist.
    """

    result = await db.execute(
        select(Package).where(Package.id == package_id)
    )
    package = result.scalars().first()

    driver_result = await db.execute(
        select(Driver).where(Driver.id == driver_id)
    )
    driver = driver_result.scalars().first()

    if not package:

        traffic_data = None

        have_destination = (
            dest_lat is not None
            and dest_lon is not None
        )

        have_origin = (
            driver is not None
            and driver.current_lat is not None
            and driver.current_lon is not None
        )

        if have_destination and have_origin:

            traffic_data = await traffic_service.get_traffic_data(
                driver.current_lat,
                driver.current_lon,
                dest_lat,
                dest_lon,
            )

        now = datetime.utcnow()

        if traffic_data is not None:

            dist = traffic_data["distance_km"]
            traffic = traffic_data["traffic_condition"]

            predicted_eta_seconds = (
                traffic_data["predicted_eta_seconds"]
            )

            actual_duration_minutes = max(
                1.0,
                predicted_eta_seconds / 60.0
                + random.normalvariate(0, 2),
            )

        else:

            dist = random.uniform(1.0, 15.0)

            traffic = random.uniform(0.0, 1.0)

            expected_duration_minutes = (
                (dist * 2.0)
                + (traffic * 20.0)
                + 2.0
            )

            predicted_eta_seconds = (
                expected_duration_minutes * 60
            )

            actual_duration_minutes = (
                expected_duration_minutes
                + random.normalvariate(0, 2)
            )

            actual_duration_minutes = max(
                1.0,
                actual_duration_minutes,
            )

        created_at_simulated = (
            now - timedelta(minutes=actual_duration_minutes)
        )

        package = Package(
            id=package_id,
            status=status,
            dest_lat=dest_lat
            if dest_lat is not None
            else 0.0,
            dest_lon=dest_lon
            if dest_lon is not None
            else 0.0,
            distance_km=dist,
            traffic_condition=traffic,
            predicted_eta_seconds=predicted_eta_seconds,
            created_at=created_at_simulated,
            loaded_at=created_at_simulated,
            updated_at=now,
        )

        db.add(package)

    package.status = status
    package.updated_at = datetime.utcnow()

    if driver:
        package.driver_id = driver.id

    await db.commit()

    return package