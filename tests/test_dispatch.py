import pytest
import time
from src.backend.services.dispatch_service import dispatch_service
from src.backend.services.heartbeat import _memory_heartbeats

@pytest.mark.asyncio
async def test_find_optimal_driver():
    """Verify that dispatch finds the closest online driver."""
    # Place D001 very close to target coordinates (41.88, -87.63)
    await dispatch_service.update_driver_coordinate("D001", 41.8790, -87.6290)
    
    # Place D002 further away
    await dispatch_service.update_driver_coordinate("D002", 42.0000, -88.0000)

    optimal_driver = await dispatch_service.find_optimal_driver(41.8781, -87.6298)
    assert optimal_driver == "D001"

@pytest.mark.asyncio
async def test_ignore_offline_driver_in_dispatch():
    """Verify that expired/offline drivers are excluded from dispatch matching."""
    driver_id = "D003"
    await dispatch_service.update_driver_coordinate(driver_id, 41.8782, -87.6299)
    
    # Force backdate heartbeat to make driver offline (>60s TTL)
    _memory_heartbeats[driver_id] = time.time() - 70
    
    # Even if closest, should not pick D003 if offline
    optimal_driver = await dispatch_service.find_optimal_driver(41.8781, -87.6298)
    assert optimal_driver != driver_id
