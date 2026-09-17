import time
import pytest
from httpx import AsyncClient
from src.backend.services.heartbeat import heartbeat_service, _memory_heartbeats

@pytest.mark.asyncio
async def test_heartbeat_service_online_status():
    """Verify that updating a driver heartbeat sets them to online and respects expiration."""
    driver_id = "D999"
    
    # Ensure clean state
    if driver_id in _memory_heartbeats:
        del _memory_heartbeats[driver_id]
        
    assert await heartbeat_service.is_online(driver_id) is False
    
    # Send heartbeat
    await heartbeat_service.update(driver_id)
    assert await heartbeat_service.is_online(driver_id) is True
    
    # Test expiration by manually backdating the timestamp past the 60s TTL
    _memory_heartbeats[driver_id] = time.time() - 65
    assert await heartbeat_service.is_online(driver_id) is False
    
    # Clean up
    if driver_id in _memory_heartbeats:
        del _memory_heartbeats[driver_id]

@pytest.mark.asyncio
async def test_heartbeat_pre_seeding_and_counts():
    """Verify pre-seeding and online count calculations."""
    count = await heartbeat_service.get_online_count()
    assert count >= 50

    last_ts = await heartbeat_service.get_last_heartbeat("D001")
    assert last_ts is not None

@pytest.mark.asyncio
async def test_driver_location_update_logic():
    """Verify core logic behind the tracking update without needing full spatial DB schema setup."""
    driver_id = "D500"
    await heartbeat_service.update(driver_id)
    assert await heartbeat_service.is_online(driver_id) is True
    last_hb = await heartbeat_service.get_last_heartbeat(driver_id)
    assert last_hb is not None
