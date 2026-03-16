"""
Integration test fixtures.

Uses in-memory SQLite (aiosqlite) with the real FastAPI app and httpx AsyncClient.
Geometry and ARRAY columns are temporarily swapped to String() before table creation
so that both DDL and ORM queries work without PostGIS.
"""
import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import String
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.backend.core.database import Base
from src.backend.api.main import app
from src.backend.api.deps import get_db, get_current_active_user
from src.backend.models.domain import User, UserRole
from src.backend.models.sql_models import User as UserSQL, Driver as DriverSQL, Package as PackageSQL
from src.backend.utils.security import get_password_hash

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

import src.backend.models.sql_models  # noqa: F401 -- register models in Base.metadata
import src.backend.models.sql_models_routing  # noqa: F401


def _patch_incompatible_columns():
    """Swap Geometry / ARRAY column types to String for SQLite compatibility.

    Returns a list of (column, original_type) tuples so the caller can restore.
    """
    from sqlalchemy import ARRAY
    try:
        from geoalchemy2 import Geometry
        _geo = Geometry
    except ImportError:
        _geo = None

    patched = []
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, ARRAY) or (_geo and isinstance(col.type, _geo)):
                patched.append((col, col.type))
                col.type = String()
    return patched


def _restore_incompatible_columns(patched):
    """Restore original column types after a test."""
    for col, orig_type in patched:
        col.type = orig_type


# ---------------------------------------------------------------------------
# DB engine per test function
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def int_db():
    """Fresh in-memory SQLite DB per test. Swaps geo/array columns to String."""
    patched = _patch_incompatible_columns()

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    _restore_incompatible_columns(patched)


# ---------------------------------------------------------------------------
# Seed helpers (called by test modules)
# ---------------------------------------------------------------------------
async def _seed_user(db: AsyncSession, username: str, password: str, role: UserRole) -> UserSQL:
    import uuid
    u = UserSQL(
        id=str(uuid.uuid4()),
        username=username,
        email=f"{username}@integration.test",
        hashed_password=get_password_hash(password),
        role=role.value,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _seed_driver(db: AsyncSession, name: str = "Test Driver") -> DriverSQL:
    import uuid
    d = DriverSQL(id=str(uuid.uuid4()), name=name, status="active")
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _seed_package(db: AsyncSession, driver_id: str = None, status: str = "pending") -> PackageSQL:
    import uuid
    p = PackageSQL(
        id=str(uuid.uuid4()),
        driver_id=driver_id,
        dest_lat=40.7128,
        dest_lon=-74.0060,
        status=status,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


def _domain_user(db_user: UserSQL) -> User:
    return User(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        role=UserRole(db_user.role),
        is_active=db_user.is_active,
    )


# ---------------------------------------------------------------------------
# App clients — DB + auth dependency overrides
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def int_client_manager(int_db):
    mgr_sql = await _seed_user(int_db, "int_manager", "Password1!", UserRole.MANAGER)
    mgr_domain = _domain_user(mgr_sql)

    app.dependency_overrides[get_db] = lambda: int_db
    app.dependency_overrides[get_current_active_user] = lambda: mgr_domain

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, int_db, mgr_sql

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def int_client_driver(int_db):
    drv_sql = await _seed_user(int_db, "int_driver", "Password1!", UserRole.DRIVER)
    drv_domain = _domain_user(drv_sql)

    app.dependency_overrides[get_db] = lambda: int_db
    app.dependency_overrides[get_current_active_user] = lambda: drv_domain

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, int_db, drv_sql

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def int_client_anon(int_db):
    app.dependency_overrides[get_db] = lambda: int_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, int_db

    app.dependency_overrides.clear()


# Expose seed helpers for import by test modules
int_db_seed_user = _seed_user
# Expose all seed helpers
int_db_seed_driver = _seed_driver
int_db_seed_package = _seed_package

