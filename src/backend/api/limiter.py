from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.backend.core.config import settings


def client_key(request: Request) -> str:
    """The real visitor, not the proxy in front of the backend.

    Every request reaches the backend from the nginx (frontend) container, so
    keying on the connection address put all users in one bucket: ten bad
    logins a minute from anyone locked everyone out. Cloudflare sets
    CF-Connecting-IP to the visitor's address (overwriting any value the
    client sent); nginx sets X-Real-IP for office/LAN browsers.
    """
    return (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-real-ip")
        or get_remote_address(request)
    )


# Use Redis-backed storage when REDIS_URL is configured so that rate-limit
# counters are shared across all Uvicorn workers and replicas.
# Falls back to thread-safe in-memory storage for local dev / unit tests.
if settings.REDIS_URL:
    limiter = Limiter(key_func=client_key, storage_uri=settings.REDIS_URL)
else:
    limiter = Limiter(key_func=client_key)
