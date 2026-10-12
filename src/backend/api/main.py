import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from src.backend.api.limiter import limiter
from src.backend.api.metrics import ACTIVE_DRIVERS
from src.backend.core.config import settings
from src.backend.core.database import AsyncSessionLocal, engine
from src.backend.core.tracing import setup_tracing
from src.backend.services.heartbeat import heartbeat_service
from src.backend.services.redis_manager import manager as ws_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and runtime directories
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOW_DEGRADED_STARTUP = os.getenv("ALLOW_DEGRADED_STARTUP", "0") == "1"


async def update_active_drivers():
    while True:
        try:
            ACTIVE_DRIVERS.set(await heartbeat_service.get_online_count())
        except Exception as e:
            logger.error(f"Error updating active drivers metric: {e}")
        await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Delivery Intelligence Platform API starting up")
    # Redis pub/sub so live updates reach dispatchers on every API instance.
    # No seeding here: accounts are created deliberately (Phase 0 removed the
    # hardcoded admin/driver passwords the old init_data() created).
    await ws_manager.connect()
    driver_metric_task = asyncio.create_task(update_active_drivers())
    yield
    logger.info("Delivery Intelligence Platform API shutting down")
    driver_metric_task.cancel()
    with suppress(asyncio.CancelledError):
        await driver_metric_task
    await ws_manager.disconnect()


app = FastAPI(
    title="Delivery Intelligence Platform API",
    version="1.3.0",
    description=(
        "Backend routing, PostGIS spatial telemetry, Redis Pub/Sub WebSockets, "
        "proof-of-delivery logging, and route optimization."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware, rate limiting, observability
# ---------------------------------------------------------------------------
# Origins come from BACKEND_CORS_ORIGINS, which config.py requires (and
# forbids "*") in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session support required by Authlib OIDC (/oidc/*)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

setup_tracing(
    app,
    service_name=settings.OTEL_SERVICE_NAME,
    service_version=settings.OTEL_SERVICE_VERSION,
    otlp_endpoint=settings.OTLP_ENDPOINT or None,
    db_engine=engine,
)

# Routes use @limiter.limit; without these, exceeding a limit is a 500, not a 429
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)

# ---------------------------------------------------------------------------
# Router registrations
# ---------------------------------------------------------------------------
def safe_include(router_import_path: str, prefix: str = "", tags: list[str] = None):
    """Include a router. A router that fails to load stops startup, because
    carrying on would silently remove a whole API. ALLOW_DEGRADED_STARTUP=1
    downgrades the failure to a warning (local debugging only)."""
    try:
        module_path, attr_name = router_import_path.rsplit(".", 1)
        mod = __import__(module_path, fromlist=[attr_name])
        router = getattr(mod, attr_name)
        app.include_router(router, prefix=prefix, tags=tags)
        logger.info(f"Successfully loaded router: {router_import_path}")
    except Exception as e:
        if not ALLOW_DEGRADED_STARTUP:
            raise RuntimeError(f"Could not load router {router_import_path}") from e
        logger.warning(f"Could not load router {router_import_path}: {e}")

# Include all core project routers
safe_include("src.backend.api.routes.websocket.router")
safe_include("src.backend.api.routes.auth.router", prefix="/auth", tags=["Auth"])
safe_include(
    "src.backend.api.routes.users.router",
    tags=["Users"],
)
safe_include("src.backend.api.routes.delivery.router", tags=["Delivery"])
safe_include("src.backend.api.routes.dispatch.router", tags=["Dispatch"])
safe_include("src.backend.api.routes.routing.router", tags=["Routing"])
safe_include("src.backend.api.routes.advanced_routing.router", tags=["Advanced Routing"])
safe_include("src.backend.api.routes.analytics.router", tags=["Analytics"])
safe_include("src.backend.api.routes.tracking.router", tags=["Tracking"])
safe_include("src.backend.api.routes.public.router", tags=["Public"])
safe_include("src.backend.api.routes.command_center.router", tags=["Command Center"])
safe_include("src.backend.api.routes.oidc.router", tags=["OIDC"])
safe_include("src.backend.api.routes.geofence.router", tags=["Geofence"])

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
app.mount("/static/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Routes & Aliases
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "online", "service": "Delivery Intelligence Platform Backend"}

# HEAD too: uptime monitors (UptimeRobot) probe with HEAD before GET.
@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.api_route("/health/ready", methods=["GET", "HEAD"])
async def readiness_check():
    """Ready only when the database answers (for load balancers / k8s)."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
