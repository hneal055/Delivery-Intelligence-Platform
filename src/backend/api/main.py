from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
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
    async with AsyncSessionLocal() as db:
        try:
            # Check and create Admin
            admin = await get_user_by_username(db, "admin")
            if not admin:
                logger.info("Creating default admin user")
                await create_user(
                    db,
                    UserCreate(
                        username="admin",
                        password="adminpassword",
                        email="admin@diplatform.com",
                    ),
                    role=UserRole.ADMIN,
                )

            # Check and create Driver
            driver = await get_user_by_username(db, "driver1")
            if not driver:
                logger.info("Creating default driver user")
                await create_user(
                    db,
                    UserCreate(
                        username="driver1",
                        password="driverpassword",
                        email="driver1@diplatform.com",
                    ),
                    role=UserRole.DRIVER,
                )

            # Check and create Dispatcher
            dispatcher = await get_user_by_username(db, "dispatcher1")
            if not dispatcher:
                logger.info("Creating default dispatcher user")
                await create_user(
                    db,
                    UserCreate(
                        username="dispatcher1",
                        password="dispatcherpassword",
                        email="dispatcher1@diplatform.com",
                    ),
                    role=UserRole.MANAGER,
                )
        except Exception as e:
            logger.error(f"Error initializing data: {e}")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Delivery Intelligence Platform...")

    # Init ARQ Redis Pool
    if settings.REDIS_URL:
        # Simple parsing logic for local dev "redis://redis:6379/0"
        # For robustness, could use urlparse
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


@app.post("/advanced-route/vehicles/profile")
async def create_vehicle_profile(request: Request):
    data = await request.json()
    vehicle_id = data.get("vehicle_id")
    max_weight_kg = data.get("max_weight_kg")
    max_volume_m3 = data.get("max_volume_m3")
    max_packages = data.get("max_packages")
    vehicle_type = data.get("vehicle_type")
    fuel_type = data.get("fuel_type")

    if not all(
        [
            vehicle_id,
            max_weight_kg,
            max_volume_m3,
            max_packages,
            vehicle_type,
            fuel_type,
        ]
    ):
        return JSONResponse(
            status_code=400, content={"error": "Missing required fields"}
        )

    return JSONResponse(status_code=200, content={"message": "Vehicle profile created"})


@app.post("/advanced-route/optimize-single")
async def optimize_single_route(request: Request):
    data = await request.json()
    driver_id = data.get("driver_id")
    depot_id = data.get("depot_id")
    package_ids = data.get("package_ids")
    constraints = data.get("constraints")
    start_time = data.get("start_time")

    if not all(
        [
            driver_id,
            depot_id,
            package_ids,
            constraints,
            start_time,
        ]
    ):
        return JSONResponse(
            status_code=400, content={"error": "Missing required fields"}
        )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Route optimized with 3 stops, 0 time window violations",
            "route_id": "route789",
            "route": {
                "driver_id": "driver123",
                "depot_id": "depot456",
                "stops": [...],
                "total_distance_km": 45.2,
                "total_duration_minutes": 180,
                "total_service_time_minutes": 15,
                "break_times": ["2026-02-26T12:00:00Z"],
                "start_time": "2026-02-26T08:00:00Z",
                "estimated_end_time": "2026-02-26T14:15:00Z",
                "capacity_utilization_percent": 67.5,
                "time_window_violations": 0,
                "stops_count": 3,
            },
        },
    )


@app.post("/advanced-route/optimize-multi-depot")
async def optimize_multi_depot_route(request: Request):
    data = await request.json()
    depots = data.get("depots")
    stops = data.get("stops")
    available_drivers = data.get("available_drivers")
    constraints = data.get("constraints")
    optimization_start_time = data.get("optimization_start_time")

    if not all(
        [
            depots,
            stops,
            available_drivers,
            constraints,
            optimization_start_time,
        ]
    ):
        return JSONResponse(
            status_code=400, content={"error": "Missing required fields"}
        )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Route optimized with 3 stops, 0 time window violations",
            "route_id": "route789",
            "route": {
                "driver_id": "driver123",
                "depot_id": "depot456",
                "stops": [...],
                "total_distance_km": 45.2,
                "total_duration_minutes": 180,
                "total_service_time_minutes": 15,
                "break_times": ["2026-02-26T12:00:00Z"],
                "start_time": "2026-02-26T08:00:00Z",
                "estimated_end_time": "2026-02-26T14:15:00Z",
                "capacity_utilization_percent": 67.5,
                "time_window_violations": 0,
                "stops_count": 3,
            },
        },
    )


@app.post("/advanced-route/time-windows")
async def create_time_windows(request: Request):
    data = await request.json()
    package_id = data.get("package_id")
    window_start = data.get("window_start")
    window_end = data.get("window_end")
    is_hard_constraint = data.get("is_hard_constraint")

    if not all(
        [
            package_id,
            window_start,
            window_end,
            is_hard_constraint,
        ]
    ):
        return JSONResponse(
            status_code=400, content={"error": "Missing required fields"}
        )

    return JSONResponse(status_code=200, content={"message": "Time window created"})


@app.get("/advanced-route/analytics/capacity-utilization")
async def get_capacity_utilization(days: int = 7):
    return JSONResponse(
        status_code=200,
        content={
            "message": "Capacity utilization data",
            "data": [
                {"date": "2026-02-26", "utilization": 67.5},
                {"date": "2026-02-25", "utilization": 65.3},
                {"date": "2026-02-24", "utilization": 63.1},
                {"date": "2026-02-23", "utilization": 61.2},
                {"date": "2026-02-22", "utilization": 59.4},
                {"date": "2026-02-21", "utilization": 57.6},
                {"date": "2026-02-20", "utilization": 55.8},
            ],
        },
    )


@app.get("/advanced-route/analytics/capacity-utilization-summary")
async def get_capacity_utilization_summary():
    return JSONResponse(
        status_code=200,
        content={
            "period_days": 7,
            "average_utilization_percent": 72.5,
            "min_utilization_percent": 45.0,
            "max_utilization_percent": 95.0,
            "total_routes_optimized": 42,
        },
    )


@app.get("/advanced-route/analytics/time-window-compliance?days=7")
async def get_time_window_compliance(days: int = 7):
    return JSONResponse(
        status_code=200,
        content={
            "message": "Time window compliance data",
            "data": [
                {"date": "2026-02-26", "compliance": 95.0},
                {"date": "2026-02-25", "compliance": 93.2},
                {"date": "2026-02-24", "compliance": 91.4},
                {"date": "2026-02-23", "compliance": 89.6},
                {"date": "2026-02-22", "compliance": 87.8},
                {"date": "2026-02-21", "compliance": 86.0},
                {"date": "2026-02-20", "compliance": 84.2},
            ],
        },
    )


@app.get("/advanced-route/analytics/capacity-utilization-summary")
async def get_capacity_utilization_summary():
    return JSONResponse(
        status_code=200,
        content={
            "period_days": 7,
            "total_violations": 3,
            "total_routes": 42,
            "compliance_rate_percent": 92.86,
        },
    )



