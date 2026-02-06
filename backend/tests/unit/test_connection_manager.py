"""Unit tests for WebSocket connection manager (Story 5.1, Task 3)."""

import asyncio
import os

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from unittest.mock import AsyncMock, MagicMock

from backend.app.ws.manager import WebSocketManager


class TestWebSocketManager:
    """Tests for WebSocket connection manager."""

    def test_initial_state_has_no_connections(self) -> None:
        """Verify manager starts with empty connections."""
        manager = WebSocketManager()
        assert len(manager._connections) == 0

    def test_connect_adds_client(self) -> None:
        """Verify connect() adds WebSocket to active connections."""
        manager = WebSocketManager()
        ws = AsyncMock()
        asyncio.run(manager.connect(ws))
        assert ws in manager._connections

    def test_connect_calls_accept(self) -> None:
        """Verify connect() calls websocket.accept()."""
        manager = WebSocketManager()
        ws = AsyncMock()
        asyncio.run(manager.connect(ws))
        ws.accept.assert_called_once()

    def test_disconnect_removes_client(self) -> None:
        """Verify disconnect() removes WebSocket from connections."""
        manager = WebSocketManager()
        ws = MagicMock()
        manager._connections.add(ws)
        manager.disconnect(ws)
        assert ws not in manager._connections

    def test_disconnect_nonexistent_client_is_safe(self) -> None:
        """Verify disconnect() is idempotent for unknown clients."""
        manager = WebSocketManager()
        ws = MagicMock()
        manager.disconnect(ws)  # Should not raise

    def test_broadcast_sends_to_all_clients(self) -> None:
        """Verify broadcast() sends message to all connected clients."""
        manager = WebSocketManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        manager._connections.add(ws1)
        manager._connections.add(ws2)

        message = {"type": "test.event", "data": {"value": 42}}
        asyncio.run(manager.broadcast(message))

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    def test_broadcast_removes_failed_client(self) -> None:
        """Verify broadcast() removes clients that fail to receive."""
        manager = WebSocketManager()
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("connection lost")
        manager._connections.add(ws_good)
        manager._connections.add(ws_bad)

        asyncio.run(manager.broadcast({"type": "test", "data": {}}))

        assert ws_good in manager._connections
        assert ws_bad not in manager._connections

    def test_broadcast_with_no_connections_is_noop(self) -> None:
        """Verify broadcast() does nothing with no connections."""
        manager = WebSocketManager()
        asyncio.run(manager.broadcast({"type": "test", "data": {}}))
        # Should not raise

    def test_multiple_connects_and_disconnects(self) -> None:
        """Verify multiple connect/disconnect cycles work correctly."""
        manager = WebSocketManager()
        clients = [AsyncMock() for _ in range(5)]

        async def connect_all():
            for ws in clients:
                await manager.connect(ws)

        asyncio.run(connect_all())
        assert len(manager._connections) == 5

        for ws in clients[:3]:
            manager.disconnect(ws)
        assert len(manager._connections) == 2
