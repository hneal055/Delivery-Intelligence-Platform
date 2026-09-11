"""
Delivery Intelligence Platform
V4 Command Center Routes
"""

import traceback

from fastapi import APIRouter

from src.backend.services.operational_state_service import (
    operational_state_service,
)

router = APIRouter(
    prefix="/api",
    tags=["Command Center"],
)


@router.get("/command-center")
async def get_command_center():

    try:
        return await operational_state_service.get_snapshot()

    except Exception as ex:

        traceback.print_exc()

        return {
            "error": str(ex),
            "error_type": type(ex).__name__,
        }
