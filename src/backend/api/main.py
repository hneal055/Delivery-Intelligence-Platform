from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.api.limiter import limiter
from src.backend.api.routes import delivery
from src.backend.api.routes import routing
from src.backend.api.routes import auth
from src.backend.api.routes import analytics # Phase 4
from src.backend.api.routes import websocket
from src.backend.api.routes import dispatch
from src.backend.api.routes import tracking
from src.backend.core.config import settings
from src.backend.api.metrics import ACTIVE_DRIVERS
from src.backend.services.heartbeat import heartbeat_service
from src.backend.core.database import AsyncSessionLocal
from src.backend.services.user_service import get_user_by_username, create_user
from src.backend.models.domain import UserCreate, UserRole
import logging
import asyncio

# Configure Logging
logging.basicConfig(level=logging.INFO)
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

async def update_active_drivers():
    while True:
        try:
            active_count = await heartbeat_service.get_online_count()
            ACTIVE_DRIVERS.set(active_count)
        except Exception as e:
            logger.error(f"Error updating active drivers metric: {e}")
        await asyncio.sleep(5)

async def init_data():
    async with AsyncSessionLocal() as db:
        try:
            # Check and create Admin
            admin = await get_user_by_username(db, "admin")
            if not admin:
                logger.info("Creating default admin user")
                await create_user(
                    db, 
                    UserCreate(username="admin", password="adminpassword", email="admin@diplatform.com"),
                    role=UserRole.ADMIN
                )
            
            # Check and create Driver
            driver = await get_user_by_username(db, "driver1")
            if not driver:
                logger.info("Creating default driver user")
                await create_user(
                    db,
                    UserCreate(username="driver1", password="driverpassword", email="driver1@diplatform.com"),
                    role=UserRole.DRIVER
                )

            # Check and create Dispatcher
            dispatcher = await get_user_by_username(db, "dispatcher1")
            if not dispatcher:
                logger.info("Creating default dispatcher user")
                await create_user(
                    db,
                    UserCreate(username="dispatcher1", password="dispatcherpassword", email="dispatcher1@diplatform.com"),
                    role=UserRole.MANAGER
                )
        except Exception as e:
            logger.error(f"Error initializing data: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_active_drivers())
    await init_data()

@app.get("/")
def root():
    return RedirectResponse(url="/docs")
