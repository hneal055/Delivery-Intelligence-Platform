import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://delivery_redis:6379")

celery_app = Celery(
    "delivery_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="telemetry.process_ping")
def process_telemetry_ping(driver_id: str, lat: float, lon: float):
    """Background task for high-frequency PostGIS telemetry aggregation."""
    return {"status": "processed", "driver_id": driver_id, "lat": lat, "lon": lon}
