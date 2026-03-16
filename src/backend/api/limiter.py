from slowapi import Limiter
from slowapi.util import get_remote_address

from src.backend.core.config import settings

# Use Redis-backed storage when REDIS_URL is configured so that rate-limit
# counters are shared across all Uvicorn workers and replicas.
# Falls back to thread-safe in-memory storage for local dev / unit tests.
if settings.REDIS_URL:
    limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
else:
    limiter = Limiter(key_func=get_remote_address)
