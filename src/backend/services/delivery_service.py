from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import random
from src.backend.models.sql_models import Driver, Package
from src.backend.services.traffic_service import traffic_service

async def update_driver_location(db: AsyncSession, driver_id: str, lat: float, lon: float, name: str = None):
    # Try to find existing driver by primary key (driver_id is the real id, e.g. "D001")
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = result.scalars().first()

    if not driver:
        # Create new driver if not found (auto-registration for simulation).
        # Use driver_id as the explicit primary key so it matches how the
        # simulator and seed data reference drivers -- do NOT let this fall
        # back to a random UUID, or lookups elsewhere in the app will
        # silently create duplicate driver rows for the same logical driver.
        driver = Driver(
            id=driver_id,
            name=name or driver_id,
            status="active"
        )
        db.add(driver)

    driver.current_lat = lat
    driver.current_lon = lon
    driver.last_updated = datetime.utcnow()

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
    # Find package
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalars().first()

    # Check if driver exists -- look up by primary key, not name
    driver_result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = driver_result.scalars().first()

    if not package:
        # Create package if missing (auto-creation for simulation)
        # GENERATING TRAINING DATA -- real traffic data when available,
        # synthetic fallback otherwise. Real data requires both a known
        # destination and the driver's current position.
        traffic_data = None
        have_destination = dest_lat is not None and dest_lon is not None
        have_origin = driver is not None and driver.current_lat is not None and driver.current_lon is not None

        if have_destination and have_origin:
            traffic_data = await traffic_service.get_traffic_data(
                driver.current_lat, driver.current_lon, dest_lat, dest_lon
            )

        now = datetime.utcnow()

        if traffic_data is not None:
            # REAL DATA (TomTom)
            dist = traffic_data["distance_km"]
            traffic = traffic_data["traffic_condition"]
            predicted_eta_seconds = traffic_data["predicted_eta_seconds"]
            actual_duration_minutes = max(1.0, predicted_eta_seconds / 60.0 + random.normalvariate(0, 2))
        else:
            # SYNTHETIC FALLBACK (no TomTom key configured, API unreachable,
            # or destination/origin unavailable) -- unchanged from before.
            dist = random.uniform(1.0, 15.0)
            traffic = random.uniform(0.0, 1.0)
            expected_duration_minutes = (dist * 2.0) + (traffic * 20.0) + 2.0
            predicted_eta_seconds = expected_duration_minutes * 60
            actual_duration_minutes = expected_duration_minutes + random.normalvariate(0, 2)
            actual_duration_minutes = max(1.0, actual_duration_minutes)  # Min 1 min

        created_at_simulated = now - timedelta(minutes=actual_duration_minutes)
        package = Package(
            id=package_id,
            status=status,
            dest_lat=dest_lat if dest_lat is not None else 0.0,
            dest_lon=dest_lon if dest_lon is not None else 0.0,

            # ML Data (real when TomTom available, synthetic otherwise)
            distance_km=dist,
            traffic_condition=traffic,
            predicted_eta_seconds=predicted_eta_seconds,

            created_at=created_at_simulated,
            loaded_at=created_at_simulated,  # Assumed loaded at creation
            updated_at=now  # Delivered now
        )
        db.add(package)

    package.status = status
    package.updated_at = datetime.utcnow()

    if driver:
        # driver.id is now the real primary key (e.g. "D013"), correctly linked.
        package.driver_id = driver.id

    await db.commit()
    return package
