import logging
from enum import Enum
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# In-memory token store for drivers
DRIVER_PUSH_TOKENS: Dict[str, str] = {}


class NotificationEvent(str, Enum):
    DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
    DELIVERY_ASSIGNED = "DELIVERY_ASSIGNED"
    DELIVERY_EXCEPTION = "DELIVERY_EXCEPTION"


def register_driver_token(
    driver_id: str,
    push_token: str,
) -> None:
    DRIVER_PUSH_TOKENS[driver_id] = push_token

    logger.info(
        "[Notifications] Registered push token for driver %s",
        driver_id,
    )


def get_driver_token(
    driver_id: str,
) -> Optional[str]:
    return DRIVERS.get(driver_id)


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
):
    if not push_token:
        return {
            "status": "skipped",
            "reason": "missing_token",
        }

    payload = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=payload,
                timeout=5.0,
            )

            return response.json()

    except Exception as exc:
        logger.error(
            "[Notifications] Push notification failed: %s",
            exc,
        )

        return {
            "status": "error",
            "message": str(exc),
        }


async def notify_driver_assignment(
    driver_id: str,
    package_id: str,
    address: str,
):
    token = get_driver_token(driver_id)

    if not token:
        return {
            "status": "skipped",
            "reason": "no_token",
        }

    return await send_push_notification(
        token,
        "New Package Assigned",
        f"Deliver {package_id} to {address}",
        {
            "package_id": package_id,
            "action": "NEW_ASSIGNMENT",
        },
    )


class NotificationService:

    async def send_notification(
        self,
        recipient_id: str,
        recipient_address: str,
        event: NotificationEvent,
    ):
        logger.info(
            "Sending notification | recipient=%s | address=%s | event=%s",
            recipient_id,
            recipient_address,
            event.value,
        )

        return {
            "status": "sent",
            "recipient_id": recipient_id,
            "recipient_address": recipient_address,
            "event": event.value,
        }

    async def notify_driver_assignment(
        self,
        driver_id: str,
        package_id: str,
        address: str,
    ):
        return await notify_driver_assignment(
            driver_id,
            package_id,
            address,
        )


notification_service = NotificationService()