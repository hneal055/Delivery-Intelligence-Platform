import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# In-memory token store for drivers (persisted in DB/Redis in prod)
DRIVER_PUSH_TOKENS: Dict[str, str] = {}

def register_driver_token(driver_id: str, push_token: str):
    DRIVER_PUSH_TOKENS[driver_id] = push_token
    logger.info(f"[Notifications] Registered push token for driver {driver_id}: {push_token}")

def get_driver_token(driver_id: str) -> Optional[str]:
    return DRIVER_PUSH_TOKENS.get(driver_id)

async def send_push_notification(push_token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None):
    if not push_token or not push_token.startswith("ExponentPushToken"):
        logger.warning(f"[Notifications] Invalid Expo push token: {push_token}")
        return {"status": "skipped", "reason": "invalid_token"}

    payload = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(EXPO_PUSH_URL, json=payload, timeout=5.0)
            result = resp.json()
            logger.info(f"[Notifications] Push notification sent: {result}")
            return result
    except Exception as e:
        logger.error(f"[Notifications] Failed to send push notification: {e}")
        return {"status": "error", "message": str(e)}

async def notify_driver_assignment(driver_id: str, package_id: str, address: str):
    token = get_driver_token(driver_id)
    if not token:
        logger.info(f"[Notifications] No push token registered for {driver_id}. Skipping alert.")
        return {"status": "skipped", "reason": "no_token"}

    title = "?? New Package Assigned!"
    body = f"Deliver {package_id} to {address}"
    return await send_push_notification(token, title, body, {"package_id": package_id, "action": "NEW_ASSIGNMENT"})
