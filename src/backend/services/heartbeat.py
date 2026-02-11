"""
Driver heartbeat service with Redis backend and in-memory fallback.
Drivers are considered "online" if a heartbeat was received within the last 60 seconds.
"""

import time
import logging
from typing import Optional

from src.backend.core.redis_client import get_redis

logger = logging.getLogger(__name__)

HEARTBEAT_TTL = 60  # seconds
REDIS_PREFIX = "driver:heartbeat:"

# In-memory fallback (used when Redis is unavailable)
_memory_heartbeats: dict[str, float] = {}


class HeartbeatService:

    async def update(self, driver_id: str):
        """Record a heartbeat for a driver."""
        redis = await get_redis()
        if redis:
            try:
                await redis.setex(f"{REDIS_PREFIX}{driver_id}", HEARTBEAT_TTL, str(time.time()))
                return
            except Exception as e:
                logger.warning(f"Redis heartbeat update failed: {e}")
        # Fallback
        _memory_heartbeats[driver_id] = time.time()

    async def is_online(self, driver_id: str) -> bool:
        """Check if a driver has a recent heartbeat."""
        redis = await get_redis()
        if redis:
            try:
                val = await redis.get(f"{REDIS_PREFIX}{driver_id}")
                return val is not None  # Key exists = within TTL = online
            except Exception as e:
                logger.warning(f"Redis heartbeat check failed: {e}")
        # Fallback
        ts = _memory_heartbeats.get(driver_id)
        if ts is None:
            return False
        return (time.time() - ts) < HEARTBEAT_TTL

    async def get_last_heartbeat(self, driver_id: str) -> Optional[float]:
        """Get the timestamp of the last heartbeat, or None."""
        redis = await get_redis()
        if redis:
            try:
                val = await redis.get(f"{REDIS_PREFIX}{driver_id}")
                return float(val) if val else None
            except Exception as e:
                logger.warning(f"Redis heartbeat get failed: {e}")
        return _memory_heartbeats.get(driver_id)

    async def get_online_count(self) -> int:
        """Count drivers currently online."""
        redis = await get_redis()
        if redis:
            try:
                keys = []
                async for key in redis.scan_iter(match=f"{REDIS_PREFIX}*"):
                    keys.append(key)
                return len(keys)
            except Exception as e:
                logger.warning(f"Redis heartbeat count failed: {e}")
        # Fallback
        now = time.time()
        return sum(1 for ts in _memory_heartbeats.values() if now - ts < HEARTBEAT_TTL)


heartbeat_service = HeartbeatService()
