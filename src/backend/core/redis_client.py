"""
Redis client module with lazy initialization and connection pooling.
Returns None when REDIS_URL is not configured (fallback to in-memory).
"""

import logging
from typing import Optional

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_initialized = False


async def get_redis():
    """Get async Redis client. Returns None if Redis is not configured."""
    global _redis_client, _initialized

    if _initialized:
        return _redis_client

    _initialized = True

    if not settings.REDIS_URL:
        logger.info("REDIS_URL not configured, using in-memory fallback")
        return None

    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()
        logger.info(f"Redis connected: {settings.REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
        _redis_client = None
        return None


def redis_available() -> bool:
    """Check if Redis client was successfully initialized."""
    return _redis_client is not None
