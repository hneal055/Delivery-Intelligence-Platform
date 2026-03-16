"""Coverage for advanced_routing analytics endpoints and health check."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest

from src.backend.api.routes.advanced_routing import (
    health_check,
    create_time_window,
    get_capacity_utilization,
    get_capacity_utilization_summary,
    get_time_window_compliance,
    TimeWindowRequest,
)


def _make_req():
    return StarletteRequest(scope={
        "type": "http", "method": "POST", "path": "/advanced-route/test",
        "query_string": b"", "headers": [], "client": ("127.0.0.1", 9000),
    })


def _empty_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result
    return db


def _rows_db(rows):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    db.execute.return_value = mock_result
    return db


# ── health check (line 78) ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_advanced_health_check():
    result = await health_check()
    assert result == {"status": "ok", "version": "1.0"}


# ── create_time_window — validation error before DB (lines 89-93) ─────────────

@pytest.mark.asyncio
async def test_create_time_window_end_before_start():
    start = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    end   = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    payload = TimeWindowRequest(
        package_id="PKG-001",
        window_start=start,
        window_end=end,
        is_hard_constraint=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        await create_time_window(request=_make_req(), payload=payload, db=AsyncMock())
    assert exc_info.value.status_code == 422


# ── capacity-utilization — empty result (lines 191-204) ──────────────────────

@pytest.mark.asyncio
async def test_capacity_utilization_empty_returns_zeros():
    result = await get_capacity_utilization(days=7, db=_empty_db())
    assert result["total_routes_optimized"] == 0
    assert result["average_utilization_percent"] == 0.0
    assert result["period_days"] == 7


# ── capacity-utilization — non-empty result (lines 206-213) ──────────────────

@pytest.mark.asyncio
async def test_capacity_utilization_with_data():
    r1 = MagicMock(capacity_utilization_percent=80.0)
    r2 = MagicMock(capacity_utilization_percent=60.0)
    result = await get_capacity_utilization(days=14, db=_rows_db([r1, r2]))
    assert result["total_routes_optimized"] == 2
    assert result["average_utilization_percent"] == 70.0
    assert result["min_utilization_percent"] == 60.0
    assert result["max_utilization_percent"] == 80.0


# ── capacity-utilization-summary — empty result (lines 222-235) ──────────────

@pytest.mark.asyncio
async def test_capacity_utilization_summary_empty():
    result = await get_capacity_utilization_summary(days=7, db=_empty_db())
    assert result["total_routes_optimized"] == 0
    assert result["average_utilization_percent"] == 0.0


# ── capacity-utilization-summary — non-empty result (lines 237-244) ──────────

@pytest.mark.asyncio
async def test_capacity_utilization_summary_with_data():
    r1 = MagicMock(capacity_utilization_percent=90.0)
    r2 = MagicMock(capacity_utilization_percent=70.0)
    result = await get_capacity_utilization_summary(days=30, db=_rows_db([r1, r2]))
    assert result["total_routes_optimized"] == 2
    assert result["average_utilization_percent"] == 80.0


# ── time-window-compliance — empty result (lines 253-265) ────────────────────

@pytest.mark.asyncio
async def test_time_window_compliance_empty():
    result = await get_time_window_compliance(days=7, db=_empty_db())
    assert result["compliance_rate_percent"] == 100.0
    assert result["total_violations"] == 0
    assert result["total_routes"] == 0


# ── time-window-compliance — with violations (lines 267-279) ─────────────────

@pytest.mark.asyncio
async def test_time_window_compliance_with_violations():
    r1 = MagicMock(time_window_violations=2)
    r2 = MagicMock(time_window_violations=0)
    result = await get_time_window_compliance(days=14, db=_rows_db([r1, r2]))
    assert result["total_routes"] == 2
    assert result["total_violations"] == 2
    assert result["compliance_rate_percent"] == 0.0


@pytest.mark.asyncio
async def test_time_window_compliance_zero_violations():
    r1 = MagicMock(time_window_violations=0)
    r2 = MagicMock(time_window_violations=0)
    result = await get_time_window_compliance(days=7, db=_rows_db([r1, r2]))
    assert result["total_routes"] == 2
    assert result["total_violations"] == 0
    assert result["compliance_rate_percent"] == 100.0
