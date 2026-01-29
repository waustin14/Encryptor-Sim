from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.ws.system_events import get_system_ws_manager

router = APIRouter()


@router.websocket("/ws/system")
async def system_events_socket(websocket: WebSocket) -> None:
    manager = get_system_ws_manager()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
