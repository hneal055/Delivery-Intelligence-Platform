import logging
import sys
from arq import cron
from src.backend.core.config import settings
from src.backend.worker.tasks import startup, shutdown, send_notification_task

# Configure logging for the worker process
logging.basicConfig(level=logging.INFO)

# Redis Settings
REDIS_SETTINGS = {
    "host": "redis",
    "port": 6379,
    "database": 0, # Use DB 0 same as backend
}

# Parse host/port from settings.REDIS_URL if available
if settings.REDIS_URL:
    # Basic parsing for "redis://host:port/db"
    # Note: arq expects a RedisSettings object or dict, but not a full connection string directly in standard run commands
    # We will let the arq CLI or the Worker class handle it using the dict above for now.
    # In a real dynamic setup, we would parse settings.REDIS_URL properly.
    pass

class WorkerSettings:
    functions = [send_notification_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS

