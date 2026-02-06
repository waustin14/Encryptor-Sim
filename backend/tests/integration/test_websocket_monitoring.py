"""Integration tests for WebSocket monitoring endpoint (Story 5.1, Task 3).

Tests verify WebSocket connection authentication, event format compliance,
and connection manager behavior.
"""

import os

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def admin_tokens(client):
    """Login as admin and return tokens dict."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert response.status_code == 200
    return response.json()["data"]


@pytest.fixture
def admin_access_token(admin_tokens):
    """Return admin access token string."""
    return admin_tokens["accessToken"]


# ---------------------------------------------------------------------------
# Task 3.3: JWT auth for WebSocket connections
# ---------------------------------------------------------------------------


class TestWebSocketAuthentication:
    """Test WebSocket JWT authentication (AC: #3)."""

    def test_websocket_connection_with_valid_jwt(self, client, admin_access_token):
        """Verify WebSocket connection succeeds with valid JWT (AC: #3)."""
        with client.websocket_connect(
            f"/api/v1/ws?token={admin_access_token}"
        ) as websocket:
            assert websocket is not None

    def test_websocket_connection_without_token_fails(self, client):
        """Verify WebSocket connection fails without JWT (AC: #3)."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws") as websocket:
                websocket.receive_text()

    def test_websocket_connection_with_empty_token_fails(self, client):
        """Verify WebSocket connection fails with empty token."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/ws?token=") as websocket:
                websocket.receive_text()

    def test_websocket_connection_with_invalid_token_fails(self, client):
        """Verify WebSocket connection fails with invalid JWT."""
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/api/v1/ws?token=invalid-token-value"
            ) as websocket:
                websocket.receive_text()

    def test_websocket_connection_with_refresh_token_fails(
        self, client, admin_tokens
    ):
        """Verify WebSocket connection fails with refresh token (not access)."""
        refresh_token = admin_tokens["refreshToken"]
        with pytest.raises(Exception):
            with client.websocket_connect(
                f"/api/v1/ws?token={refresh_token}"
            ) as websocket:
                websocket.receive_text()


# ---------------------------------------------------------------------------
# Task 3.4-3.6: Connection manager and event format
# ---------------------------------------------------------------------------


class TestWebSocketEventFormat:
    """Test WebSocket event format compliance (AC: #4, #5)."""

    def test_broadcast_sends_correct_event_format(self, client, admin_access_token):
        """Verify broadcast events follow { type, data } structure (AC: #5)."""
        from backend.app.ws.monitoring import get_monitoring_ws_manager

        manager = get_monitoring_ws_manager()

        with client.websocket_connect(
            f"/api/v1/ws?token={admin_access_token}"
        ) as websocket:
            # Broadcast a test event
            event = {
                "type": "tunnel.status_changed",
                "data": {
                    "peerId": 1,
                    "peerName": "site-a",
                    "status": "up",
                    "timestamp": "2026-02-04T12:00:00Z",
                },
            }
            asyncio.run(manager.broadcast(event))

            data = None
            for _ in range(5):
                candidate = websocket.receive_json()
                if (
                    candidate.get("type") == "tunnel.status_changed"
                    and candidate.get("data", {}).get("timestamp")
                    == "2026-02-04T12:00:00Z"
                ):
                    data = candidate
                    break
            assert data is not None
            assert data["type"] == "tunnel.status_changed"
            assert "data" in data
            assert data["data"]["peerId"] == 1
            assert data["data"]["status"] == "up"

    def test_tunnel_status_event_uses_dot_notation(
        self, client, admin_access_token
    ):
        """Verify tunnel events use dot-notation names (AC: #4)."""
        from backend.app.ws.monitoring import get_monitoring_ws_manager

        manager = get_monitoring_ws_manager()

        with client.websocket_connect(
            f"/api/v1/ws?token={admin_access_token}"
        ) as websocket:
            event = {
                "type": "tunnel.status_changed",
                "data": {"peerId": 1, "status": "down", "timestamp": "2026-02-04T12:00:00Z"},
            }
            asyncio.run(manager.broadcast(event))

            data = websocket.receive_json()
            assert "." in data["type"]
            assert data["type"] == "tunnel.status_changed"

    def test_interface_stats_event_format(self, client, admin_access_token):
        """Verify interface.stats_updated event has correct format (AC: #4, #5, #7)."""
        from backend.app.ws.monitoring import get_monitoring_ws_manager

        manager = get_monitoring_ws_manager()

        with client.websocket_connect(
            f"/api/v1/ws?token={admin_access_token}"
        ) as websocket:
            event = {
                "type": "interface.stats_updated",
                "data": {
                    "interface": "CT",
                    "bytesRx": 1024000,
                    "bytesTx": 2048000,
                    "packetsRx": 1500,
                    "packetsTx": 2000,
                    "errorsRx": 0,
                    "errorsTx": 0,
                    "timestamp": "2026-02-04T12:00:01Z",
                },
            }
            asyncio.run(manager.broadcast(event))

            data = None
            for _ in range(6):
                candidate = websocket.receive_json()
                if (
                    candidate.get("type") == "interface.stats_updated"
                    and candidate.get("data", {}).get("timestamp")
                    == "2026-02-04T12:00:01Z"
                ):
                    data = candidate
                    break
            assert data is not None
            assert data["type"] == "interface.stats_updated"
            assert data["data"]["interface"] == "CT"
            assert "bytesRx" in data["data"]
            assert "bytesTx" in data["data"]
            assert "packetsRx" in data["data"]
            assert "packetsTx" in data["data"]
            assert "errorsRx" in data["data"]
            assert "errorsTx" in data["data"]
            assert "timestamp" in data["data"]

    def test_tunnel_status_values_are_valid(self, client, admin_access_token):
        """Verify tunnel status values match spec (AC: #6)."""
        from backend.app.ws.monitoring import get_monitoring_ws_manager

        manager = get_monitoring_ws_manager()

        valid_statuses = ["up", "down", "negotiating", "unknown"]
        for status in valid_statuses:
            with client.websocket_connect(
                f"/api/v1/ws?token={admin_access_token}"
            ) as websocket:
                event = {
                    "type": "tunnel.status_changed",
                    "data": {
                        "peerId": 1,
                        "status": status,
                        "timestamp": "2026-02-04T12:00:00Z",
                    },
                }
                asyncio.run(manager.broadcast(event))

                data = websocket.receive_json()
                assert data["data"]["status"] in valid_statuses

    def test_initial_snapshot_includes_telemetry_schema(
        self, client, admin_access_token
    ):
        """Verify connect-time snapshot includes full telemetry fields (AC: #6)."""

        def mock_send_command(cmd: str):
            if cmd == "get_tunnel_telemetry":
                return {
                    "result": {
                        "1": {
                            "status": "up",
                            "establishedSec": 3600,
                            "bytesIn": 1000,
                            "bytesOut": 2000,
                            "packetsIn": 10,
                            "packetsOut": 20,
                        }
                    }
                }
            if cmd == "get_interface_stats":
                return {"result": {}}
            return {"result": {}}

        peers = [SimpleNamespace(peerId=1, name="site-a")]
        with (
            patch("backend.app.ws.monitoring._load_peers", return_value=peers),
            patch("backend.app.ws.monitoring.send_command", side_effect=mock_send_command),
        ):
            with client.websocket_connect(
                f"/api/v1/ws?token={admin_access_token}"
            ) as websocket:
                data = websocket.receive_json()

        assert data["type"] == "tunnel.status_changed"
        assert data["data"]["peerId"] == 1
        assert data["data"]["peerName"] == "site-a"
        assert data["data"]["status"] == "up"
        assert data["data"]["establishedSec"] == 3600
        assert data["data"]["bytesIn"] == 1000
        assert data["data"]["bytesOut"] == 2000
        assert data["data"]["packetsIn"] == 10
        assert data["data"]["packetsOut"] == 20
        assert "isPassingTraffic" in data["data"]
        assert "lastTrafficAt" in data["data"]
        assert "timestamp" in data["data"]

    def test_initial_snapshot_falls_back_to_status_when_telemetry_unavailable(
        self, client, admin_access_token
    ):
        """Verify snapshot status still updates when telemetry is unavailable (AC: #8)."""

        def mock_send_command(cmd: str):
            if cmd == "get_tunnel_telemetry":
                return {"result": {}}
            if cmd == "get_tunnel_status":
                return {"result": {"1": "up"}}
            if cmd == "get_interface_stats":
                return {"result": {}}
            return {"result": {}}

        peers = [SimpleNamespace(peerId=1, name="site-a")]
        with (
            patch("backend.app.ws.monitoring._load_peers", return_value=peers),
            patch("backend.app.ws.monitoring.send_command", side_effect=mock_send_command),
        ):
            with client.websocket_connect(
                f"/api/v1/ws?token={admin_access_token}"
            ) as websocket:
                data = websocket.receive_json()

        assert data["type"] == "tunnel.status_changed"
        assert data["data"]["status"] == "up"
        assert data["data"]["establishedSec"] == 0
        assert data["data"]["bytesIn"] == 0
        assert data["data"]["bytesOut"] == 0
