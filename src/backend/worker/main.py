import logging
from urllib.parse import urlparse
from arq import cron
from arq.connections import RedisSettings
from src.backend.core.config import settings
from src.backend.worker.tasks import startup, shutdown, send_notification_task

# Configure logging for the worker process
logging.basicConfig(level=logging.INFO)

# Build RedisSettings from REDIS_URL (e.g. redis://:password@host:port/db)
def _redis_settings_from_url(url: str) -> RedisSettings:
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "redis",
        port=parsed.port or 6379,
        database=int((parsed.path or "/0").lstrip("/") or 0),
        password=parsed.password or None,
    )

REDIS_SETTINGS = _redis_settings_from_url(
    settings.REDIS_URL or "redis://redis:6379/0"
)

class WorkerSettings:
    functions = [send_notification_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS
