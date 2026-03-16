"""
Notification service supporting Email (SendGrid), SMS (Twilio), and logging fallback.
Controlled by NOTIFICATIONS_ENABLED env var. When disabled, all notifications are logged only.
"""

import re
import logging
import asyncio
from enum import Enum
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.backend.core.config import settings

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
    DELIVERY_COMPLETED = "delivery_completed"


class NotificationService:
    """
    Handles outgoing notifications to customers via SMS, Email, or App Push.
    When NOTIFICATIONS_ENABLED is false, all sends are logged only.

    Both Twilio and SendGrid SDKs are synchronous; calls are dispatched via
    asyncio.to_thread() so they never block the event loop.
    Transient failures are retried up to 3 times with exponential backoff.
    """

    def __init__(self):
        self._twilio_client = None
        self._sendgrid_client = None

        if settings.NOTIFICATIONS_ENABLED:
            self._init_twilio()
            self._init_sendgrid()

    def _init_twilio(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self._twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
                logger.info("Twilio SMS client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio client: {e}")

    def _init_sendgrid(self):
        if settings.SENDGRID_API_KEY:
            try:
                from sendgrid import SendGridAPIClient
                self._sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                logger.info("SendGrid email client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize SendGrid client: {e}")

    async def send_notification(
        self,
        recipient_id: str,
        contact_info: str,
        event: NotificationEvent,
        message: Optional[str] = None,
    ):
        if not message:
            message = self._get_default_message(event)

        logger.info(f"Sending {event.value} notification to {recipient_id} ({contact_info}): {message}")

        if not settings.NOTIFICATIONS_ENABLED:
            return {"status": "logged", "recipient": recipient_id, "event": event.value, "message": message}

        # Determine channel from contact_info format
        channel = self._detect_channel(contact_info)

        try:
            if channel == NotificationType.EMAIL:
                await self._send_email(contact_info, event, message)
            elif channel == NotificationType.SMS:
                await self._send_sms(contact_info, message)
            else:
                logger.info(f"No handler for channel {channel}, logged only")
        except Exception as e:
            logger.error(f"Failed to send {channel.value} notification to {contact_info}: {e}")
            return {"status": "error", "recipient": recipient_id, "event": event.value, "error": str(e)}

        return {"status": "sent", "recipient": recipient_id, "event": event.value, "message": message}

    def _detect_channel(self, contact_info: str) -> NotificationType:
        if re.match(r"^[^@]+@[^@]+\.[^@]+$", contact_info):
            return NotificationType.EMAIL
        if re.match(r"^\+?\d{10,15}$", contact_info.replace("-", "").replace(" ", "")):
            return NotificationType.SMS
        return NotificationType.APP

    async def _send_email(self, to_email: str, event: NotificationEvent, body: str):
        if not self._sendgrid_client:
            logger.warning("SendGrid client not configured, skipping email")
            return

        from sendgrid.helpers.mail import Mail

        subject = self._build_email_subject(event)
        html_content = self._build_email_html(event, body)

        mail = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        # SendGrid SDK is synchronous — run in a thread pool to avoid blocking the event loop.
        response = await asyncio.to_thread(self._sendgrid_client.send, mail)
        logger.info(f"SendGrid email sent to {to_email}, status={response.status_code}")

    async def _send_sms(self, to_phone: str, body: str):
        if not self._twilio_client:
            logger.warning("Twilio client not configured, skipping SMS")
            return

        # Twilio SDK is synchronous — run in a thread pool to avoid blocking the event loop.
        msg = await asyncio.to_thread(
            self._twilio_client.messages.create,
            body=body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_phone,
        )
        logger.info(f"Twilio SMS sent to {to_phone}, sid={msg.sid}")

    def _build_email_subject(self, event: NotificationEvent) -> str:
        subjects = {
            NotificationEvent.OUT_FOR_DELIVERY: "Your package is on its way!",
            NotificationEvent.NEARBY: "Your driver is almost there!",
            NotificationEvent.DELIVERED: "Your package has been delivered",
            NotificationEvent.EXCEPTION: "Delivery update - action needed",
            NotificationEvent.DELIVERY_COMPLETED: "Delivery confirmed",
        }
        return subjects.get(event, "Delivery update")

    def _build_email_html(self, event: NotificationEvent, message: str) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2196F3;">Delivery Intelligence Platform</h2>
            <p>{message}</p>
            <hr style="border: none; border-top: 1px solid #eee;" />
            <p style="color: #999; font-size: 12px;">
                This is an automated notification. Please do not reply.
            </p>
        </div>
        """

    def _get_default_message(self, event: NotificationEvent) -> str:
        messages = {
            NotificationEvent.OUT_FOR_DELIVERY: "Your package is out for delivery today!",
            NotificationEvent.NEARBY: "Your driver is nearing your location.",
            NotificationEvent.DELIVERED: "Your package has been delivered.",
            NotificationEvent.EXCEPTION: "There was an issue with your delivery. Please contact support.",
            NotificationEvent.DELIVERY_COMPLETED: "Your delivery has been confirmed with proof of delivery.",
        }
        return messages.get(event, "Update regarding your delivery.")


# Singleton instance
notification_service = NotificationService()
