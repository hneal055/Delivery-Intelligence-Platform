from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from src.backend.api.routes import users
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq import create_pool
from arq.connections import RedisSettings
from typing import Optional

from src.backend.api.limiter import limiter
from src.backend.api.routes import delivery
from src.backend.api.routes import routing
from src.backend.api.routes import auth
from src.backend.api.routes import oidc
from src.backend.api.routes import analytics
from src.backend.api.routes import websocket
from src.backend.api.routes import dispatch
from src.backend.api.routes import tracking
from src.backend.api.routes import advanced_routing
from src.backend.core.config import settings
from src.backend.core.tracing import setup_tracing
from src.backend.api.metrics import ACTIVE_DRIVERS
from src.backend.services.heartbeat import heartbeat_service
from src.backend.core.database import AsyncSessionLocal, engine
from src.backend.services.user_service import get_user_by_username, create_user
from src.backend.models.domain import UserCreate, UserRole
from src.backend.models.sql_models import Driver
from src.backend.services.redis_manager import manager as ws_manager
from src.backend.core.logging_config import configure_logging
import logging
import asyncio

# Configure Logging
configure_logging()
logger = logging.getLogger(__name__)


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

                # Driver profile (used by simulator -- must use explicit D001 IDs)
                result = await db.execute(select(Driver).where(Driver.id == driver_id))
                existing_driver = result.scalars().first()
                if not existing_driver:
                    db.add(Driver(
                        id=driver_id,
                        name=f"Driver {i:03d}",
                        status="active",
                    ))
                    created_profiles += 1

            await db.commit()
            if created_users or created_profiles:
                logger.info(f"Seeding complete: {created_users} users, {created_profiles} driver profiles created")
            else:
                logger.info("Seed data already present, skipping")

        except Exception as e:
            logger.error(f"Error during init_data: {e}")
            await db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: replaces deprecated @app.on_event handlers."""
    logger.info("Starting up...")
    await ws_manager.connect()
    await init_data()
    driver_metric_task = asyncio.create_task(update_active_drivers())
    logger.info("Startup complete")

    yield  # ← application runs here

    logger.info("Shutting down...")
    driver_metric_task.cancel()
    with suppress(asyncio.CancelledError):
        await driver_metric_task
    await ws_manager.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
# Session support required by Authlib OIDC
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)
# --- OpenTelemetry Tracing ---
# Called immediately after app creation so all route registrations are captured.
setup_tracing(
    app,
    service_name=settings.OTEL_SERVICE_NAME,
    service_version=settings.OTEL_SERVICE_VERSION,
    otlp_endpoint=settings.OTLP_ENDPOINT or None,
    db_engine=engine,
)

# --- CORS Configuration ---
_CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_CORS_ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "Origin",
    "X-Requested-With",
    "X-DIAD-Token",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=_CORS_ALLOWED_METHODS,
    allow_headers=_CORS_ALLOWED_HEADERS,
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus Metrics
Instrumentator().instrument(app).expose(app)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(oidc.router)
app.include_router(routing.router)
app.include_router(delivery.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(dispatch.router)
app.include_router(tracking.router)
app.include_router(advanced_routing.router)
app.include_router(users.router)

@app.get("/health")
async def health_check():
    return {"status": "online"}


@app.get("/health/ready")
async def readiness_check():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")


_DEV_DEVICE_TOKEN = "dev-secret-key-123"


@app.post("/secure-ping")
async def secure_ping(x_diad_token: Optional[str] = Header(default=None, alias="X-DIAD-Token")):
    if x_diad_token != _DEV_DEVICE_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid device token")
    return {"msg": "Device Authenticated"}


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")