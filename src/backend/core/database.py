from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from src.backend.core.config import settings

# Create async engine
# Ensure the URL starts with postgresql+asyncpg:// for async support
database_url = settings.DATABASE_URL
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    # Production pool tuning: support up to 20 concurrent queries per replica,
    # with up to 10 extra connections allowed during traffic spikes.
    # pool_timeout: raise after 30 s waiting for a free connection (not block forever).
    # pool_recycle: discard connections older than 30 min to avoid PG idle-in-transaction kills.
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,   # validates connections before use — survives PG restarts
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
