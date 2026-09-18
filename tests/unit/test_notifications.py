import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.services import notifications as notif_module

@pytest.fixture(autouse=True)
def mock_config_settings():
    with patch("src.backend.core.config.settings") as mock_set:
        mock_set.NOTIFICATIONS_ENABLED = True
        yield mock_set

@pytest.mark.asyncio
async def test_send_notification_success():
    svc = notif_module.NotificationService()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = await svc.send_notification(
            recipient_id="user-123",
            recipient_address="test@example.com",
            event=notif_module.NotificationEvent.DELIVERY_ASSIGNED
        )
        assert result is not None

@pytest.mark.asyncio
async def test_notify_driver_assignment():
    with patch("src.backend.services.notifications.get_driver_token", return_value="dummy-token"), \
         patch("src.backend.services.notifications.send_push_notification", new_callable=AsyncMock) as mock_push:
        
        mock_push.return_value = {"status": "success"}

        result = await notif_module.notify_driver_assignment(
            driver_id="drv-123",
            package_id="pkg-456",
            address="123 Main St"
        )
        assert result is not None
        mock_push.assert_awaited_once()
