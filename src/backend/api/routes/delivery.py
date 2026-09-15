from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Request,
)
from fastapi.responses import Response
from pydantic import BaseModel

import time

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.models.domain import Location, User
from src.backend.api.deps import get_current_active_user
from src.backend.core.database import get_db
from src.backend.core.storage import (
    proof_storage,
    is_safe_filename,
)
from src.backend.services import delivery_service
from src.backend.services.notifications import (
    notification_service,
    NotificationEvent,
)
from src.backend.api.limiter import limiter
from src.backend.api.metrics import (
    driver_heartbeats,
    DELIVERIES_COMPLETED,
)

router = APIRouter(
    prefix="/delivery",
    tags=["delivery"],
)


class LocationVerifyRequest(BaseModel):
    driver_id: str = "unknown"
    current_location: Location
    target_delivery_location: Location


@router.get("/health")
async def health():
    return {
        "status": "ok"
    }