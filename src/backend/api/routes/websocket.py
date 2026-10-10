import json
import logging
import time
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from src.backend.core.config import settings
from src.backend.core.permissions import Permission, ROLE_PERMISSIONS
from src.backend.models.domain import UserRole
from src.backend.services.redis_manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)

def validate_ws_token(token: str) -> dict:
    """Validate JWT token from WebSocket query param. Returns payload or raises."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username:
            return None
        return {"username": username, "role": role}
    except JWTError:
        return None


def _can_manage_jobs(role: str) -> bool:
    try:
        return Permission.MANAGE_JOBS in ROLE_PERMISSIONS.get(UserRole(role), set())
    except ValueError:
        return False


@router.websocket("/ws/dispatch")
async def dispatch_ws(websocket: WebSocket, token: str = Query(...)):
    user = validate_ws_token(token)
    # Same rule as the REST dispatch endpoints: anyone who can manage jobs
    # (dispatcher, manager, admin) gets the live dispatch feed.
    if not user or not _can_manage_jobs(user["role"]):
        await websocket.close(code=4003, reason="Forbidden")
        return

    user_id = user["username"]
    await manager.connect_dispatcher(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "assign_delivery":
                    driver_id = msg.get("driver_id")
                    await manager.send_to_driver(driver_id, {
                        "type": "new_assignment",
                        "package_id": msg.get("package_id"),
                        "dispatcher": user_id,
                        "timestamp": time.time(),
                    })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect_client(user_id, websocket)


@router.websocket("/ws/driver/{driver_id}")
async def driver_ws(websocket: WebSocket, driver_id: str, token: str = Query(...)):
    user = validate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect_driver(websocket, driver_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "location_update":
                    await manager.broadcast_to_dispatchers({
                        "type": "driver_location",
                        "driver_id": driver_id,
                        "lat": msg.get("lat"),
                        "lon": msg.get("lon"),
                        "speed_kmh": msg.get("speed_kmh"),
                        "heading": msg.get("heading"),
                        "timestamp": time.time(),
                    })

                elif msg_type == "status_update":
                    await manager.broadcast_to_dispatchers({
                        "type": "driver_status",
                        "driver_id": driver_id,
                        "status": msg.get("status"),
                        "timestamp": time.time(),
                    })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect_client(driver_id, websocket)