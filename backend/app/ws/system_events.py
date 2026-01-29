from __future__ import annotations

from typing import Any

from backend.app.ws.manager import WebSocketManager


_manager = WebSocketManager()


def get_system_ws_manager() -> WebSocketManager:
    return _manager


def emit_isolation_status_updated(data: dict[str, Any]) -> None:
    message = {"type": "system.isolation_status_updated", "data": data}
    manager = get_system_ws_manager()
    # Fire-and-forget broadcast for current connections.
    try:
        import asyncio

        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(message))
    except RuntimeError:
        import asyncio

        asyncio.run(manager.broadcast(message))
