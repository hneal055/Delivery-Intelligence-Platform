from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import random
from src.backend.models.sql_models import Driver, Package

async def update_driver_location(db: AsyncSession, driver_id: str, lat: float, lon: float, name: str = None):
    # Try to find existing driver
    result = await db.execute(select(Driver).where(Driver.name == driver_id)) # Using name as ID for now based on simulator
    driver = result.scalars().first()
    
    if not driver:
        # Create new driver if not found (auto-registration for simulation)
        driver = Driver(
            name=driver_id,
            status="active"
        )
        db.add(driver)
    
    driver.current_lat = lat
    driver.current_lon = lon
    driver.last_updated = datetime.utcnow()
    
    await db.commit()
    await db.refresh(driver)
    return driver

async def update_package_status(db: AsyncSession, package_id: str, status: str, driver_id: str):
    # Find package
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalars().first()
    
    # Check if driver exists
    driver_result = await db.execute(select(Driver).where(Driver.name == driver_id))
    driver = driver_result.scalars().first()
    
    if not package:
        # Create package if missing (auto-creation for simulation)
        # GENERATING SYNTHETIC ML DATA FOR TRAINING
        
        # 1. Simulate randomized features
        dist = random.uniform(1.0, 15.0)
        traffic = random.uniform(0.0, 1.0)
        
        # 2. Calculate "Expected" Duration (matches the generator logic)
        # Delay = (Dist * 2) + (Traffic * 20) + (Pkgs=1 * 2) + Noise
        expected_duration_minutes = (dist * 2.0) + (traffic * 20.0) + 2.0
        predicted_eta_seconds = expected_duration_minutes * 60
        
        # 3. Add noise to Actual Duration to make it realistic
        actual_duration_minutes = expected_duration_minutes + random.normalvariate(0, 2)
        actual_duration_minutes = max(1.0, actual_duration_minutes) # Min 1 min
        
        # 4. Backdate created_at so that (now - created_at) == actual_duration
        now = datetime.utcnow()
        created_at_simulated = now - timedelta(minutes=actual_duration_minutes)

        package = Package(
            id=package_id,
            status=status,
            dest_lat=0.0, # Placeholder
            dest_lon=0.0, # Placeholder
            
            # ML Data
            distance_km=dist,
            traffic_condition=traffic,
            predicted_eta_seconds=predicted_eta_seconds,
            
            created_at=created_at_simulated,
            loaded_at=created_at_simulated, # Assumed loaded at creation
            updated_at=now # Delivered now
        )
        db.add(package)
    
    package.status = status
    package.updated_at = datetime.utcnow()
    
    if driver:
        # Link driver. Note: SQL model expects driver.id (uuid), but our simulator uses names.
        # We need to link to the UUID of the driver we found/created.
        package.driver_id = driver.id
        
    await db.commit()
    return package
