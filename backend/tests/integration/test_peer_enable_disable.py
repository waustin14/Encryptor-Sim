"""Integration tests for peer enable/disable behavior (Story 5.3).

Tests verify that enabling and disabling peers properly calls daemon IPC,
handles daemon unavailability gracefully, and broadcasts WebSocket events.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture(autouse=True)
def _clean_peers():
    """Remove all peers before each test for isolation."""
    from backend.app.db.deps import get_db_session
    from backend.app.models.peer import Peer

    gen = get_db_session()
    session = next(gen)
    try:
        session.query(Peer).delete()
        session.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def admin_tokens(client):
    """Login as admin and return tokens."""
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


class TestPeerEnableDisable:
    """Tests for peer enable/disable functionality."""

    def test_create_peer_with_enabled_true(self, client, admin_access_token):
        """Test creating a peer with enabled=true."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            response = client.post(
                "/api/v1/peers",
                json={
                    "name": "test-peer",
                    "remoteIp": "10.0.0.1",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["enabled"] is True
            assert data["data"]["name"] == "test-peer"

    def test_create_peer_with_enabled_false(self, client, admin_access_token):
        """Test creating a peer with enabled=false."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            # Daemon should NOT be called for disabled peer creation
            response = client.post(
                "/api/v1/peers",
                json={
                    "name": "disabled-peer",
                    "remoteIp": "10.0.0.2",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["enabled"] is False

            # Daemon configure_peer should not be called for disabled peer
            mock_send.assert_not_called()

    def test_disable_peer_calls_teardown(self, client, admin_access_token):
        """Test that disabling a peer calls daemon teardown and remove_peer_config."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create an enabled peer
            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-to-disable",
                    "remoteIp": "10.0.0.3",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            mock_send.reset_mock()

            # Disable the peer
            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"enabled": False},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            data = update_response.json()
            assert data["data"]["enabled"] is False

            # Verify daemon was called for teardown and remove_peer_config
            assert mock_send.call_count == 2
            calls = [call[0][0] for call in mock_send.call_args_list]
            assert "teardown_peer" in calls
            assert "remove_peer_config" in calls

    def test_enable_peer_calls_configure(self, client, admin_access_token):
        """Test that enabling a peer calls daemon configure_peer."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create a disabled peer
            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-to-enable",
                    "remoteIp": "10.0.0.4",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            mock_send.reset_mock()

            # Enable the peer
            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"enabled": True},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            data = update_response.json()
            assert data["data"]["enabled"] is True

            # Verify daemon was called for configure_peer
            mock_send.assert_called()
            commands = [call[0][0] for call in mock_send.call_args_list]
            assert "configure_peer" in commands

    def test_enable_peer_resyncs_routes(self, client, admin_access_token):
        """Test that enabling a peer re-syncs peer routes via daemon IPC."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create disabled peer
            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-with-routes",
                    "remoteIp": "10.0.0.7",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            # Add route while peer disabled (should persist in DB)
            route_response = client.post(
                "/api/v1/routes",
                json={"peerId": peer_id, "destinationCidr": "192.168.77.0/24"},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert route_response.status_code == 201

            mock_send.reset_mock()

            # Enable the peer
            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"enabled": True},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert update_response.status_code == 200

            commands = [call[0][0] for call in mock_send.call_args_list]
            assert "configure_peer" in commands
            assert "update_routes" in commands

    def test_disable_peer_emits_down_event(self, client, admin_access_token):
        """Test that disabling a peer broadcasts tunnel.status_changed down event."""
        manager = type("Manager", (), {"broadcast": AsyncMock()})()
        with patch("backend.app.api.peers.send_command") as mock_send, patch(
            "backend.app.api.peers.get_monitoring_ws_manager"
        ) as mock_manager:
            mock_send.return_value = {"status": "ok", "result": {"message": "ok"}}
            mock_manager.return_value = manager

            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-event-disable",
                    "remoteIp": "10.0.0.8",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            manager.broadcast.reset_mock()

            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"enabled": False},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            tunnel_events = [
                call for call in manager.broadcast.await_args_list
                if call[0][0].get("type") == "tunnel.status_changed"
            ]
            assert len(tunnel_events) == 1
            event = tunnel_events[0][0][0]
            assert event["data"]["status"] == "down"
            assert event["data"]["peerId"] == peer_id

    def test_delete_peer_returns_envelope_and_emits_down_event(
        self, client, admin_access_token
    ):
        """Test delete teardown response envelope and down event emission."""
        manager = type("Manager", (), {"broadcast": AsyncMock()})()
        with patch("backend.app.api.peers.send_command") as mock_send, patch(
            "backend.app.api.peers.get_monitoring_ws_manager"
        ) as mock_manager:
            mock_send.return_value = {"status": "ok", "result": {"message": "ok"}}
            mock_manager.return_value = manager

            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-event-delete",
                    "remoteIp": "10.0.0.9",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            manager.broadcast.reset_mock()
            mock_send.reset_mock()

            delete_response = client.delete(
                f"/api/v1/peers/{peer_id}",
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert delete_response.status_code == 200
            body = delete_response.json()
            assert body["data"]["peerId"] == peer_id
            assert "meta" in body
            assert "daemonAvailable" in body["meta"]
            tunnel_events = [
                call for call in manager.broadcast.await_args_list
                if call[0][0].get("type") == "tunnel.status_changed"
            ]
            assert len(tunnel_events) >= 1

    def test_disable_with_daemon_unavailable_succeeds(self, client, admin_access_token):
        """Test that disabling succeeds even when daemon is unavailable."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create an enabled peer
            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-daemon-fail",
                    "remoteIp": "10.0.0.5",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            # Make daemon unavailable for disable
            mock_send.side_effect = ConnectionError("Daemon unavailable")

            # Disable should still succeed
            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"enabled": False},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            data = update_response.json()
            assert data["data"]["enabled"] is False
            assert "warning" in data["meta"]
            assert data["meta"]["daemonAvailable"] is False

    def test_update_without_changing_enabled_no_transition(self, client, admin_access_token):
        """Test that updating other fields without changing enabled doesn't trigger transition logic."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create an enabled peer
            create_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "peer-no-change",
                    "remoteIp": "10.0.0.6",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert create_response.status_code == 201
            peer_id = create_response.json()["data"]["peerId"]

            mock_send.reset_mock()

            # Update name only (no enabled change)
            update_response = client.put(
                f"/api/v1/peers/{peer_id}",
                json={"name": "peer-renamed"},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            data = update_response.json()
            assert data["data"]["enabled"] is True
            assert data["data"]["name"] == "peer-renamed"

            # Only configure_peer should be called (for regular update)
            assert mock_send.call_count == 1
            assert mock_send.call_args[0][0] == "configure_peer"
