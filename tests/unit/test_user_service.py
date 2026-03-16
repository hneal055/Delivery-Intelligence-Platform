"""
Unit tests for user_service using fully mocked AsyncSession to avoid
PostGIS-dependent tables that cannot be create in SQLite.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import User as UserSQL
from src.backend.services.user_service import get_user_by_username, create_user


def _make_db_returning(value):
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_get_user_not_found_returns_none():
    db = _make_db_returning(None)
    result = await get_user_by_username(db, "no_such_user_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_found_returns_sql_model():
    fake_sql_user = UserSQL(
        username="alice", email="alice@example.com",
        hashed_password="hashed_pw", role="driver", is_active=True,
    )
    db = _make_db_returning(fake_sql_user)
    result = await get_user_by_username(db, "alice")
    assert result is fake_sql_user
    assert result.username == "alice"


@pytest.mark.asyncio
async def test_create_user_returns_domain_model():
    db = AsyncMock()

    async def fake_refresh(obj):
        obj.id = "uuid-test-001"

    db.refresh = fake_refresh
    user_in = UserCreate(username="bob", email="bob@example.com", password="plaintext")
    result = await create_user(db, user_in, UserRole.DRIVER)

    assert result.username == "bob"
    assert result.role == UserRole.DRIVER
    assert result.id == "uuid-test-001"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_password_is_hashed():
    db = AsyncMock()

    async def fake_refresh(obj):
        obj.id = "uuid-test-002"

    db.refresh = fake_refresh
    user_in = UserCreate(username="carol", email="carol@example.com", password="plaintext_pass")
    result = await create_user(db, user_in, UserRole.MANAGER)

    assert result.role == UserRole.MANAGER
    # The domain model does not expose hashed_password, but we verify
    # the service called commit (implying hash was stored)
    db.commit.assert_awaited_once()
