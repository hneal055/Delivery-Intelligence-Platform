"""
Unit tests for the NotificationService.
All external calls (Twilio, SendGrid) are mocked so tests run offline.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.backend.services.notifications import (
    NotificationService,
    NotificationEvent,
    NotificationType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(enabled: bool = True, has_twilio: bool = True, has_sendgrid: bool = True):
    """Build a NotificationService with mocked dependencies."""
    svc = NotificationService.__new__(NotificationService)
    svc._twilio_client = MagicMock() if (enabled and has_twilio) else None
    svc._sendgrid_client = MagicMock() if (enabled and has_sendgrid) else None

    # Patch settings on the module so the service reads enabled=True
    import src.backend.services.notifications as notif_module
    notif_module.settings.NOTIFICATIONS_ENABLED = enabled
    notif_module.settings.TWILIO_FROM_NUMBER = "+10000000000"
    notif_module.settings.SENDGRID_FROM_EMAIL = "noreply@test.com"
    return svc


# ---------------------------------------------------------------------------
# Channel detection
# ---------------------------------------------------------------------------

class TestDetectChannel:
    def setup_method(self):
        self.svc = _make_service()

    def test_email_detected(self):
        assert self.svc._detect_channel("user@example.com") == NotificationType.EMAIL

    def test_phone_detected(self):
        assert self.svc._detect_channel("+12025551234") == NotificationType.SMS

    def test_phone_with_dashes_detected(self):
        assert self.svc._detect_channel("+1-202-555-1234") == NotificationType.SMS

    def test_unknown_channel_falls_back_to_app(self):
        assert self.svc._detect_channel("user_id_12345") == NotificationType.APP


# ---------------------------------------------------------------------------
# Default messages
# ---------------------------------------------------------------------------

class TestDefaultMessages:
    def setup_method(self):
        self.svc = _make_service()

    def test_out_for_delivery_message(self):
        msg = self.svc._get_default_message(NotificationEvent.OUT_FOR_DELIVERY)
        assert "out for delivery" in msg.lower()

    def test_delivered_message(self):
        msg = self.svc._get_default_message(NotificationEvent.DELIVERED)
        assert "delivered" in msg.lower()

    def test_exception_message(self):
        msg = self.svc._get_default_message(NotificationEvent.EXCEPTION)
        assert "issue" in msg.lower() or "problem" in msg.lower() or "support" in msg.lower()


# ---------------------------------------------------------------------------
# Disabled mode: all sends are no-ops that return "logged"
# ---------------------------------------------------------------------------

class TestDisabledMode:
    @pytest.mark.asyncio
    async def test_returns_logged_status_when_disabled(self):
        svc = _make_service(enabled=False)
        result = await svc.send_notification(
            recipient_id="R001",
            contact_info="user@example.com",
            event=NotificationEvent.DELIVERED,
        )
        assert result["status"] == "logged"
        assert result["recipient"] == "R001"

    @pytest.mark.asyncio
    async def test_no_external_calls_when_disabled(self):
        svc = _make_service(enabled=False)
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            await svc.send_notification("R001", "user@example.com", NotificationEvent.DELIVERED)
            mock_thread.assert_not_called()


# ---------------------------------------------------------------------------
# Email sending (enabled, mocked SendGrid)
# ---------------------------------------------------------------------------

class TestEmailSending:
    @pytest.mark.asyncio
    async def test_send_email_calls_sendgrid_via_thread(self):
        svc = _make_service(enabled=True, has_sendgrid=True)
        mock_response = MagicMock()
        mock_response.status_code = 202

        # Stub the sendgrid module so the lazy import inside _send_email works
        # even when the real package is not installed in the dev venv.
        import sys
        from types import ModuleType

        sg_helpers = ModuleType("sendgrid.helpers.mail")
        sg_helpers.Mail = MagicMock(return_value=MagicMock())
        sg_module = ModuleType("sendgrid")

        with patch.dict(sys.modules, {"sendgrid": sg_module, "sendgrid.helpers": ModuleType("sendgrid.helpers"), "sendgrid.helpers.mail": sg_helpers}):
            with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_response):
                result = await svc.send_notification(
                    recipient_id="R002",
                    contact_info="customer@example.com",
                    event=NotificationEvent.OUT_FOR_DELIVERY,
                )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_email_without_client_is_no_op(self):
        svc = _make_service(enabled=True, has_sendgrid=False)
        # Should not raise even with no client
        await svc._send_email("user@example.com", NotificationEvent.DELIVERED, "msg")


# ---------------------------------------------------------------------------
# SMS sending (enabled, mocked Twilio)
# ---------------------------------------------------------------------------

class TestSmsSending:
    @pytest.mark.asyncio
    async def test_send_sms_calls_twilio_via_thread(self):
        svc = _make_service(enabled=True, has_twilio=True)
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_msg):
            result = await svc.send_notification(
                recipient_id="R003",
                contact_info="+12025551234",
                event=NotificationEvent.NEARBY,
            )

        assert result["status"] == "sent"

    @pytest.mark.asyncio
    async def test_send_sms_without_client_is_no_op(self):
        svc = _make_service(enabled=True, has_twilio=False)
        await svc._send_sms("+12025551234", "test message")

    @pytest.mark.asyncio
    async def test_send_failure_returns_error_status(self):
        svc = _make_service(enabled=True, has_twilio=True)

        with patch("asyncio.to_thread", new_callable=AsyncMock, side_effect=Exception("Network error")):
            result = await svc.send_notification(
                recipient_id="R004",
                contact_info="+12025551234",
                event=NotificationEvent.EXCEPTION,
            )

        assert result["status"] == "error"
        assert "Network error" in result["error"]

