from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from src.backend.api.limiter import limiter
from src.backend.api.routes import delivery
from src.backend.api.routes import routing
from src.backend.api.routes import auth
from src.backend.api.routes import analytics # Phase 4
from src.backend.core.config import settings
from src.backend.api.metrics import ACTIVE_DRIVERS, driver_heartbeats
import logging
import asyncio
import time

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

async def update_active_drivers():
    while True:
        try:
            now = time.time()
            # Count drivers seen in last 60 seconds
            active_count = sum(1 for ts in driver_heartbeats.values() if now - ts < 60)
            ACTIVE_DRIVERS.set(active_count)
        except Exception as e:
            logger.error(f"Error updating active drivers metric: {e}")
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_active_drivers())

@app.get("/")
def root():
    return RedirectResponse(url="/docs")
