import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.services import delivery_service
from src.backend.models.sql_models import Package


@pytest.mark.asyncio
async def test_update_package_status_success():
    """Test that update_package_status correctly updates an existing package status."""
    db_session = AsyncMock(spec=AsyncSession)
    mock_package = Package(id="pkg-123", status="pending")
    
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = mock_package
    db_session.execute.return_value = mock_result

    await delivery_service.update_package_status(
        db=db_session,
        package_id="pkg-123",
        status="delivered",
        driver_id="drv-456"
    )

    assert mock_package.status == "delivered"
    db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_driver_location_success():
    """Test that update_driver_location successfully records driver coordinates."""
    db_session = AsyncMock(spec=AsyncSession)
    
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    db_session.execute.return_value = mock_result

    await delivery_service.update_driver_location(
        db=db_session,
        driver_id="drv-456",
        lat=41.8781,
        lon=-87.6298,
        name="Howard Neal"
    )

    db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_package_status_create_new_with_traffic():
    """Test creating a new package when it doesn't exist, utilizing traffic service data."""
    db_session = AsyncMock(spec=AsyncSession)
    
    mock_pkg_result = MagicMock()
    mock_pkg_result.scalars().first.return_value = None
    
    mock_driver_result = MagicMock()
    mock_driver = MagicMock()
    mock_driver.current_lat = 41.8781
    mock_driver.current_lon = -87.6298
    mock_driver_result.scalars().first.return_value = mock_driver

    db_session.execute.side_effect = [mock_pkg_result, mock_driver_result]

    mock_traffic = {
        "distance_km": 5.0,
        "traffic_condition": 0.2,
        "predicted_eta_seconds": 600
    }

    # Patch whatever traffic function delivery_service calls (we will verify via inspection above)
    with patch("src.backend.services.delivery_service.traffic_service") as mock_traffic_svc:
        mock_traffic_svc.get_traffic_data = AsyncMock(return_value=mock_traffic)

        await delivery_service.update_package_status(
            db=db_session,
            package_id="pkg-new-999",
            status="dispatched",
            driver_id="drv-456",
            dest_lat=41.8900,
            dest_lon=-87.6500
        )

        db_session.add.assert_called_once()
        db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_package_status_create_new_without_traffic():
    """Test creating a new package when traffic service returns None (fallback branch)."""
    db_session = AsyncMock(spec=AsyncSession)
    
    mock_pkg_result = MagicMock()
    mock_pkg_result.scalars().first.return_value = None
    
    mock_driver_result = MagicMock()
    mock_driver_result.scalars().first.return_value = None

    db_session.execute.side_effect = [mock_pkg_result, mock_driver_result]

    with patch("src.backend.services.delivery_service.traffic_service") as mock_traffic_svc:
        mock_traffic_svc.get_traffic_data = AsyncMock(return_value=None)

        await delivery_service.update_package_status(
            db=db_session,
            package_id="pkg-new-888",
            status="pending",
            driver_id="drv-456",
            dest_lat=41.8900,
            dest_lon=-87.6500
        )

        db_session.add.assert_called_once()
        db_session.commit.assert_awaited()
