import logging
import asyncio
from src.backend.services.notifications import notification_service, NotificationEvent, NotificationType

logger = logging.getLogger(__name__)

async def send_notification_task(ctx, recipient_id: str, contact_info: str, event_value: str, message: str = None):
    """
    Task to send a notification via the NotificationService.
    ARGuments must be serializable (str, int, dict), so we pass enum values as strings.
    """
    event = NotificationEvent(event_value)
    logger.info(f"[Worker] Processing notification for {recipient_id} ({event_value})")
    
    # Simulate slight delay to prove async nature
    await asyncio.sleep(0.1)
    
    await notification_service.send_notification(
        recipient_id=recipient_id,
        contact_info=contact_info,
        event=event,
        message=message
    )
    return f"Sent {event_value} to {recipient_id}"

async def startup(ctx):
    logger.info("Worker starting up...")
    # Initialize implementation-specific services if needed
    # notification_service is already init on import

async def shutdown(ctx):
    logger.info("Worker shutting down...")

