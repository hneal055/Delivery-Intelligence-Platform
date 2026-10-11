import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "delivery_proofs.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@delivery_db:5432/delivery_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://delivery_redis:6379")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Delivery Intelligence Platform API starting up")
    yield
    logger.info("Delivery Intelligence Platform API shutting down")

app = FastAPI(
    title="Delivery Intelligence Platform API",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}