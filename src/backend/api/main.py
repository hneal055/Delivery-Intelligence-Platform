from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq import create_pool
from arq.connections import RedisSettings

from src.backend.api.limiter import limiter
from src.backend.api.routes import delivery
from src.backend.api.routes import routing
from src.backend.api.routes import auth
from src.backend.api.routes import analytics  # Phase 4
from src.backend.api.routes import websocket
from src.backend.api.routes import dispatch
from src.backend.api.routes import tracking
from src.backend.api.routes import advanced_routing
from src.backend.core.config import settings
from src.backend.api.metrics import ACTIVE_DRIVERS
from src.backend.services.heartbeat import heartbeat_service
from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import get_user_by_username, create_user
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import Driver
from src.backend.services.redis_manager import manager as ws_manager
from src.backend.core.logging_config import configure_logging
import logging
import asyncio
import requests

# Configure Logging
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus Metrics
Instrumentator().instrument(app).expose(app)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(routing.router)
app.include_router(delivery.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(dispatch.router)
app.include_router(tracking.router)
app.include_router(advanced_routing.router)


async def update_active_drivers():
    while True:
        try:
            active_count = await heartbeat_service.get_online_count()
            ACTIVE_DRIVERS.set(active_count)
        except Exception as e:
            logger.error(f"Error updating active drivers metric: {e}")
        await asyncio.sleep(5)


async def init_data():
    """Idempotent startup seed: creates admin, dispatcher, and 50 driver
    user accounts (driver1-driver50) plus their D001-D050 driver profiles."""
    async with AsyncSessionLocal() as db:
        try:
            # --- Auth users ---
            admin = await get_user_by_username(db, "admin")
            if not admin:
                logger.info("Seeding: admin user")
                await create_user(
                    db,
                    UserCreate(username="admin", password="adminpassword", email="admin@diplatform.com"),
                    role=UserRole.ADMIN,
                )

            dispatcher = await get_user_by_username(db, "dispatcher1")
            if not dispatcher:
                logger.info("Seeding: dispatcher1 user")
                await create_user(
                    db,
                    UserCreate(username="dispatcher1", password="dispatcherpassword", email="dispatcher1@diplatform.com"),
                    role=UserRole.MANAGER,
                )

            # --- 50 driver user accounts + driver profiles (D001-D050) ---
            created_users = 0
            created_profiles = 0

            for i in range(1, 51):
                username = f"driver{i}"
                driver_id = f"D{i:03d}"

                # User account
                existing_user = await get_user_by_username(db, username)
                if not existing_user:
                    await create_user(
                        db,
                        UserCreate(username=username, password="driverpassword", email=f"{username}@diplatform.com"),
                        role=UserRole.DRIVER,
                    )
                    created_users += 1

                # Driver profile (used by simulator — must use explicit D001 IDs)
                result = await db.execute(select(Driver).where(Driver.id == driver_id))
                if not result.scalars().first():
                    db.add(Driver(
                        id=driver_id,
                        name=f"Driver {i}",
                        status="active",
                        vehicle_id=f"V-{i:03d}",
                        current_lat=41.8781,   # Chicago default
                        current_lon=-87.6298,
                    ))
                    created_profiles += 1

            await db.commit()

            if created_users or created_profiles:
                logger.info(f"Seeding complete: +{created_users} driver users, +{created_profiles} driver profiles")
            else:
                logger.info("Seed data already present — no changes made")

        except Exception as e:
            logger.error(f"Error initializing data: {e}")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Delivery Intelligence Platform...")

    # Init ARQ Redis Pool
    if settings.REDIS_URL:
        try:
            app.state.arq_pool = await create_pool(
                RedisSettings(host="redis", port=6379, database=0)
            )
            logger.info("ARQ Redis pool initialized")
        except Exception as e:
            logger.error(f"Failed to init ARQ pool: {e}")
            app.state.arq_pool = None

    await init_data()
    await ws_manager.connect()
    asyncio.create_task(update_active_drivers())


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "arq_pool") and app.state.arq_pool:
        await app.state.arq_pool.close()


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
