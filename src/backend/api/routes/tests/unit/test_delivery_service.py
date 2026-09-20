import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.services.delivery_service import DeliveryService
from src.backend.models.sql_models import Package


@pytest.mark.asyncio
async def test_delivery_service_confirm_success():
    """Test that DeliveryService successfully updates a package status to delivered and saves proof."""
    db_session = AsyncMock(spec=AsyncSession)
    mock_package = Package(id="pkg-123", driver_id="drv-456", status="pending")
    
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = mock_package
    db_session.execute.return_value = mock_result

    service = DeliveryService(db_session)
    
    with patch("src.backend.core.storage.proof_storage.save_proof", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "storage/proofs/pkg-123_drv-456_12345.jpg"
        
        result = await service.confirm_delivery(
            package_id="pkg-123",
            driver_id="drv-456",
            file_bytes=b"fake-jpeg-bytes",
            filename="proof.jpg"
        )

        assert result["status"] == "success" or mock_package.status == "delivered"
        mock_save.assert_awaited_once()
        db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_delivery_service_report_exception():
    """Test that DeliveryService correctly logs a delivery exception against a package."""
    db_session = AsyncMock(spec=AsyncSession)
    mock_package = Package(id="pkg-123", driver_id="drv-456", status="pending")
    
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = mock_package
    db_session.execute.return_value = mock_result

    service = DeliveryService(db_session)
    
    result = await service.report_exception(
        package_id="pkg-123",
        driver_id="drv-456",
        reason="Recipient unavailable"
    )

    assert mock_package.status == "exception"
    db_session.commit.assert_awaited()