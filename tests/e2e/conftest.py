"""
E2E test fixtures — requires a real PostgreSQL + PostGIS database.

Set E2E_DATABASE_URL to run:

    E2E_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/delivery_e2e \
        pytest tests/e2e/ -m e2e

All tests in this directory are marked @pytest.mark.e2e and are skipped
when E2E_DATABASE_URL is absent so the standard CI suite is unaffected.
"""

import os

import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from src.backend.api.deps import get_db
from src.backend.api.main import app
from src.backend.core.database import Base

# Ensure all models are registered in Base.metadata
import src.backend.models.sql_models  # noqa: F401
import src.backend.models.sql_models_routing  # noqa: F401


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

E2E_DATABASE_URL = os.getenv(
    "E2E_DATABASE_URL",
    "",
)


# ---------------------------------------------------------------------------
# E2E Database Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def e2e_engine():
    """
    Session-scoped real PostgreSQL/PostGIS engine.

    IMPORTANT:
    We skip here instead of at module import time so that
    unit/integration/smoke tests can still be collected when
    E2E_DATABASE_URL is not configured.
    """

    if not E2E_DATABASE_URL:
        pytest.skip(
            "E2E_DATABASE_URL not set — skipping PostGIS E2E tests"
        )

    engine = create_async_engine(
        E2E_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS postgis")
        )

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_db(e2e_engine):
    """
    Per-test transactional session.
    """

    Session = sessionmaker(
        e2e_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def e2e_client(e2e_db):
    """
    HTTP client wired to the real PostGIS-backed session.
    """

    app.dependency_overrides[get_db] = lambda: e2e_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac, e2e_db

    app.dependency_overrides.pop(
        get_db,
        None,
    )