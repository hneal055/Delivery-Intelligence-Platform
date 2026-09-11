"""
Simple heartbeat service.
"""

import time

HEARTBEAT_TTL = 60

_memory_heartbeats = {}


class HeartbeatService:

    async def update(self, driver_id: str):
        _memory_heartbeats[driver_id] = time.time()

    async def is_online(self, driver_id: str) -> bool:
        ts = _memory_heartbeats.get(driver_id)

        if ts is None:
            return False

        return (time.time() - ts) < HEARTBEAT_TTL

    async def get_last_heartbeat(self, driver_id: str):
        return _memory_heartbeats.get(driver_id)

    async def get_online_count(self) -> int:
        now = time.time()

        return sum(
            1
            for ts in _memory_heartbeats.values()
            if (now - ts) < HEARTBEAT_TTL
        )


heartbeat_service = HeartbeatService()