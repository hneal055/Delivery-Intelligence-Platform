from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from src.backend.websockets.manager import manager
import json
import logging

router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("delivery_platform.ws_router")

@router.websocket("/ws/dispatcher")
async def dispatcher_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer token for authentication")
):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message from dispatcher client: {data}")
            await websocket.send_text(json.dumps({"status": "acknowledged"}))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
