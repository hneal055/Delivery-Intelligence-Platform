import logging
import json
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import redis.asyncio as aioredis
import os

logger = logging.getLogger("delivery_platform.driver_status")
router = APIRouter(prefix="/api/drivers", tags=["Driver Status"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class StatusUpdateRequest(BaseModel):
    driver_id: str
    order_id: str
    status: str  # e.g., "accepted", "en_route", "arrived", "delivered"
    notes: str | None = None

@router.post("/status", status_code=status.HTTP_200_OK)
async def update_driver_status(payload: StatusUpdateRequest):
    valid_statuses = {"accepted", "en_route", "arrived", "delivered", "delayed"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {list(valid_statuses)}"
        )

    event_payload = {
        "event": "driver_status_update",
        "data": {
            "driver_id": payload.driver_id,
            "order_id": payload.order_id,
            "status": payload.status,
            "notes": payload.notes
        }
    }

    try:
        client = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.publish("fleet_telemetry_channel", json.dumps(event_payload))
        await client.close()
    except Exception as e:
        logger.error(f"Failed to publish driver status update to Redis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast status update."
        )

    logger.info(f"Driver {payload.driver_id} updated order {payload.order_id} status to: {payload.status}")
    return {"status": "success", "driver_id": payload.driver_id, "order_status": payload.status}
