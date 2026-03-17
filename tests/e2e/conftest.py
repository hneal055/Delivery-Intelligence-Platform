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

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

# Skip the entire module collection when no real DB is provided
E2E_DATABASE_URL = os.getenv("E2E_DATABASE_URL", "")

if not E2E_DATABASE_URL:
    pytest.skip(
        "E2E_DATABASE_URL not set — skipping PostGIS E2E tests",
        allow_module_level=True,
    )

from src.backend.core.database import Base
from src.backend.api.main import app
from src.backend.api.deps import get_db

# Ensure all models are registered in Base.metadata
import src.backend.models.sql_models          # noqa: F401
import src.backend.models.sql_models_routing  # noqa: F401


@pytest_asyncio.fixture(scope="session")
async def e2e_engine():
    """Session-scoped real PostgreSQL engine; drops/recreates schema each run."""
    engine = create_async_engine(E2E_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        # Ensure PostGIS extension exists
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_db(e2e_engine):
    """Per-test transactional session; rolls back after each test."""
    Session = sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def e2e_client(e2e_db):
    """HTTP client wired to the real PostGIS-backed session."""
    app.dependency_overrides[get_db] = lambda: e2e_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, e2e_db
    app.dependency_overrides.pop(get_db, None)