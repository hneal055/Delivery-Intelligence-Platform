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
            text(
                "CREATE EXTENSION IF NOT EXISTS postgis"
            )
        )

        await conn.run_sync(
            Base.metadata.drop_all
        )

        await conn.run_