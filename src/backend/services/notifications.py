from enum import Enum
from typing import Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    APP = "app"

class NotificationEvent(Enum):
    OUT_FOR_DELIVERY = "out_for_delivery"
    NEARBY = "nearby"
    DELIVERED = "delivered"
    EXCEPTION = "exception"

class NotificationService:
    """
    Handles outgoing notifications to customers via SMS, Email, or App Push.
    Implementation of Requirement 1.2.6
    """

    def __init__(self):
        # In a real impl, inject clients (e.g., Twilio, SendGrid, Firebase) here
        pass

    async def send_notification(self, 
                                recipient_id: str, 
                                contact_info: str, 
                                event: NotificationEvent, 
                                message: Optional[str] = None):
        """
        Dispatches a notification based on the event type.
        """
        if not message:
            message = self._get_default_message(event)

        # Logic to determine channel preference for user would go here.
        # Defaulting to logging for MVP/Skeleton.
        
        logger.info(f"Sending {event.value} notification to {recipient_id} ({contact_info}): {message}")
        
        # Simulation of sending
        return {
            "status": "sent", 
            "recipient": recipient_id, 
            "event": event.value,
            "message": message
        }

    def _get_default_message(self, event: NotificationEvent) -> str:
        messages = {
            NotificationEvent.OUT_FOR_DELIVERY: "Your package is out for delivery today!",
            NotificationEvent.NEARBY: "Your driver is nearing your location.",
            NotificationEvent.DELIVERED: "Your package has been delivered.",
            NotificationEvent.EXCEPTION: "There was an issue with your delivery. Please contact support."
        }
        return messages.get(event, "Update regarding your delivery.")

# Singleton instance
notification_service = NotificationService()
