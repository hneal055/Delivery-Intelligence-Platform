"""
Firebase Cloud Messaging service for push notifications to mobile driver app.
Disabled when FIREBASE_CREDENTIALS_JSON is empty.
"""

import json
import logging
from typing import Optional, List

from src.backend.core.config import settings

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _init_firebase():
    """Initialize Firebase Admin SDK. Called lazily on first send."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    creds_path = settings.FIREBASE_CREDENTIALS_JSON
    if not creds_path:
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if creds_path.startswith("{"):
            cred = credentials.Certificate(json.loads(creds_path))
        else:
            cred = credentials.Certificate(creds_path)

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase: {e}")
        return False


async def send_push(device_token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
    """Send a push notification to a single device."""
    if not _init_firebase():
        logger.debug("Firebase not configured, skipping push notification")
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=device_token,
        )
        response = messaging.send(message)
        logger.info(f"FCM push sent: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM send error: {e}")
        return False


async def send_push_batch(tokens: List[str], title: str, body: str, data: Optional[dict] = None) -> int:
    """Send push notification to multiple devices. Returns count of successful sends."""
    if not tokens or not _init_firebase():
        return 0

    try:
        from firebase_admin import messaging

        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=token,
            )
            for token in tokens
        ]
        response = messaging.send_each(messages)
        success_count = response.success_count
        logger.info(f"FCM batch sent: {success_count}/{len(tokens)} successful")
        return success_count
    except Exception as e:
        logger.error(f"FCM batch send error: {e}")
        return 0
