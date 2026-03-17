import os
# Disable OTel SDK during tests to prevent background exporter thread noise on teardown
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
"""
Shared pytest fixtures for the Delivery Intelligence Platform test suite.

Uses an in-memory SQLite database (via aiosqlite) so tests never need a
running PostgreSQL instance.  PostGIS-specific types are excluded from the
in-memory schema; geofencing logic is tested as pure-Python unit tests.
"""
import pytest
import pytest_asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.backend.core.database import Base
from src.backend.api.main import app
from src.backend.api.deps import get_current_active_user, get_db
from src.backend.models.domain import User, UserRole
from src.backend.utils.security import create_access_token, get_password_hash


# ---------------------------------------------------------------------------
# In-memory async SQLite engine (no PostGIS, no real PG required)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create a fresh in-memory SQLite DB for each test function."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Import all SQL models so Base has their metadata
    import src.backend.models.sql_models  # noqa: F401

    async with engine.begin() as conn:
        # SQLite does not support PostGIS geometry columns; skip them at DDL time
        # by filtering out tables that rely on Geography/Geometry types.
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# Fake users
# ---------------------------------------------------------------------------

def make_user(username: str, role: UserRole) -> User:
    return User(
        id="test-uuid-" + username,
        username=username,
        email=f"{username}@test.com",
        role=role,
        is_active=True,
    )


@pytest.fixture
def driver_user():
    return make_user("driver_test", UserRole.DRIVER)


@pytest.fixture
def manager_user():
    return make_user("manager_test", UserRole.MANAGER)


@pytest.fixture
def admin_user():
    return make_user("admin_test", UserRole.ADMIN)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def make_token(user: User) -> str:
    return create_access_token(subject=user.username, role=user.role, expires_delta=timedelta(hours=1))


@pytest.fixture
def driver_token(driver_user):
    return make_token(driver_user)


@pytest.fixture
def manager_token(manager_user):
    return make_token(manager_user)


@pytest.fixture
def admin_token(admin_user):
    return make_token(admin_user)


# ---------------------------------------------------------------------------
# HTTPX AsyncClient with app + overridden dependencies
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client_driver(test_db, driver_user):
    """Async test client authenticated as a driver."""
    from httpx import AsyncClient, ASGITransport

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_active_user] = lambda: driver_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_manager(test_db, manager_user):
    """Async test client authenticated as a manager."""
    from httpx import AsyncClient, ASGITransport

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_active_user] = lambda: manager_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_anon(test_db):
    """Unauthenticated async test client."""
    from httpx import AsyncClient, ASGITransport

    app.dependency_overrides[get_db] = lambda: test_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

