"""
Push alerts to a driver's phone(s) for new assignments and ready pickups.

The app registers its Expo push token at login (POST /auth/register-device);
tokens are stored per user in device_tokens. Look the tokens up inside the
request (the DB session closes afterwards), then send in a background task
so a slow push service never delays dispatch.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.sql_models import DeviceToken, Package, User
from src.backend.services.notifications import send_push_notification

logger = logging.getLogger(__name__)


async def driver_push_tokens(db: AsyncSession, username: str) -> List[str]:
    result = await db.execute(
        select(DeviceToken.token)
        .join(User, User.id == DeviceToken.user_id)
        .where(User.username == username)
    )
    return [row[0] for row in result.all()]


async def _send_all(tokens: List[str], title: str, body: str, data: Dict[str, Any]) -> None:
    for token in tokens:
        result = await send_push_notification(token, title, body, data)
        logger.info("Push to driver device: %s", result)


async def alert_driver(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    username: Optional[str],
    package: Package,
    kind: str,
) -> None:
    """kind: "assigned" (new work) or "ready" (pickup is ready)."""
    if not username:
        return
    tokens = await driver_push_tokens(db, username)
    if not tokens:
        return

    if kind == "ready":
        title = "Ready for pickup"
        body = package.pickup_address or package.dest_address or package.id
    elif package.pickup_address:
        title = "New pickup & delivery"
        body = f"Pick up at {package.pickup_address}"
    else:
        title = "New delivery"
        body = package.dest_address or package.id

    data = {"kind": kind, "package_id": package.id}
    background_tasks.add_task(_send_all, tokens, title, body, data)
