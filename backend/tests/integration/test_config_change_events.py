"""Integration tests for config-change WebSocket event broadcasts (Story 5.5, Task 3).

Tests verify that peer/route/interface mutation endpoints broadcast
config-change events over WebSocket for UI reflection.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture(autouse=True)
def _clean_data():
    """Remove all routes and peers before each test."""
    from backend.app.db.deps import get_db_session
    from backend.app.models.peer import Peer
    from backend.app.models.route import Route

    gen = get_db_session()
    session = next(gen)
    try:
        session.query(Route).delete()
        session.query(Peer).delete()
        session.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def admin_access_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    return response.json()["data"]["accessToken"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_peer(client, token, name="event-peer", remote_ip="10.1.1.100"):
    resp = client.post(
        "/api/v1/peers",
        headers=_auth_header(token),
        json={
            "name": name,
            "remoteIp": remote_ip,
            "psk": "super-secret-key",
            "ikeVersion": "ikev2",
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _create_route(client, token, peer_id, cidr="192.168.1.0/24"):
    resp = client.post(
        "/api/v1/routes",
        headers=_auth_header(token),
        json={"peerId": peer_id, "destinationCidr": cidr},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


class TestPeerConfigChangedEvent:
    """Verify peer mutations broadcast peer.config_changed events (AC: #6)."""

    def test_peer_create_broadcasts_config_changed(self, client, admin_access_token):
        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/peers",
                headers=_auth_header(admin_access_token),
                json={
                    "name": "broadcast-peer",
                    "remoteIp": "10.0.0.1",
                    "psk": "key",
                    "ikeVersion": "ikev2",
                },
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "peer.config_changed"
            ]
            assert len(broadcast_calls) == 1
            event = broadcast_calls[0][0][0]
            assert event["data"]["action"] == "created"

    def test_peer_update_broadcasts_config_changed(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)

        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.put(
                f"/api/v1/peers/{peer['peerId']}",
                headers=_auth_header(admin_access_token),
                json={"dpdDelay": 45},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "peer.config_changed"
            ]
            assert len(broadcast_calls) == 1
            assert broadcast_calls[0][0][0]["data"]["action"] == "updated"

    def test_peer_delete_broadcasts_config_changed(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)

        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.delete(
                f"/api/v1/peers/{peer['peerId']}",
                headers=_auth_header(admin_access_token),
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "peer.config_changed"
            ]
            assert len(broadcast_calls) == 1
            assert broadcast_calls[0][0][0]["data"]["action"] == "deleted"

    def test_peer_config_changed_event_shape(self, client, admin_access_token):
        """Verify event follows { type, data } convention with dot-notation."""
        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/peers",
                headers=_auth_header(admin_access_token),
                json={
                    "name": "shape-peer",
                    "remoteIp": "10.0.0.2",
                    "psk": "key",
                    "ikeVersion": "ikev2",
                },
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "peer.config_changed"
            ]
            event = broadcast_calls[0][0][0]
            assert "type" in event
            assert "data" in event
            assert "." in event["type"]  # dot-notation
            assert "peerId" in event["data"]
            assert "action" in event["data"]


class TestRouteConfigChangedEvent:
    """Verify route mutations broadcast route.config_changed events (AC: #6)."""

    def test_route_create_broadcasts_config_changed(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)

        with patch("backend.app.api.routes.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/routes",
                headers=_auth_header(admin_access_token),
                json={"peerId": peer["peerId"], "destinationCidr": "10.0.0.0/8"},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "route.config_changed"
            ]
            assert len(broadcast_calls) == 1
            event = broadcast_calls[0][0][0]
            assert event["data"]["action"] == "created"
            assert event["data"]["peerId"] == peer["peerId"]

    def test_route_update_broadcasts_config_changed(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        with patch("backend.app.api.routes.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.put(
                f"/api/v1/routes/{route['routeId']}",
                headers=_auth_header(admin_access_token),
                json={"destinationCidr": "172.16.0.0/12"},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "route.config_changed"
            ]
            assert len(broadcast_calls) == 1
            assert broadcast_calls[0][0][0]["data"]["action"] == "updated"

    def test_route_delete_broadcasts_config_changed(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        with patch("backend.app.api.routes.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.delete(
                f"/api/v1/routes/{route['routeId']}",
                headers=_auth_header(admin_access_token),
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "route.config_changed"
            ]
            assert len(broadcast_calls) == 1
            assert broadcast_calls[0][0][0]["data"]["action"] == "deleted"

    def test_route_config_changed_event_shape(self, client, admin_access_token):
        """Verify route event includes routeId and peerId."""
        peer = _create_peer(client, admin_access_token)

        with patch("backend.app.api.routes.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/routes",
                headers=_auth_header(admin_access_token),
                json={"peerId": peer["peerId"], "destinationCidr": "10.0.0.0/8"},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "route.config_changed"
            ]
            event = broadcast_calls[0][0][0]
            assert "type" in event
            assert "data" in event
            assert "." in event["type"]
            assert "routeId" in event["data"]
            assert "peerId" in event["data"]
            assert "action" in event["data"]


class TestInterfaceConfigChangedEvent:
    """Verify interface mutations broadcast interface.config_changed events (AC: #6)."""

    def test_interface_configure_broadcasts_config_changed(
        self, client, admin_access_token, monkeypatch
    ):
        import backend.app.api.interfaces

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {"status": "success", "isolation": {"status": "pass"}},
        })
        monkeypatch.setattr(backend.app.api.interfaces, "send_command", mock_send)

        with patch("backend.app.api.interfaces.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/interfaces/ct/configure",
                headers=_auth_header(admin_access_token),
                json={"ipAddress": "10.0.0.1", "netmask": "255.255.255.0", "gateway": "10.0.0.254"},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "interface.config_changed"
            ]
            assert len(broadcast_calls) == 1
            event = broadcast_calls[0][0][0]
            assert event["data"]["action"] == "updated"
            assert event["data"]["interface"] == "ct"

    def test_interface_config_changed_event_shape(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify interface event follows { type, data } with dot-notation."""
        import backend.app.api.interfaces

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {"status": "success", "isolation": {"status": "pass"}},
        })
        monkeypatch.setattr(backend.app.api.interfaces, "send_command", mock_send)

        with patch("backend.app.api.interfaces.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.post(
                "/api/v1/interfaces/ct/configure",
                headers=_auth_header(admin_access_token),
                json={"ipAddress": "10.0.0.1", "netmask": "255.255.255.0", "gateway": "10.0.0.254"},
            )

            broadcast_calls = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "interface.config_changed"
            ]
            event = broadcast_calls[0][0][0]
            assert "type" in event
            assert "data" in event
            assert "." in event["type"]
            assert "interface" in event["data"]
            assert "action" in event["data"]


class TestExistingEventCompatibility:
    """Verify existing monitoring events are not broken (AC: #8, Task 3.3)."""

    def test_peer_delete_still_emits_tunnel_status_down(self, client, admin_access_token):
        """Verify delete still emits tunnel.status_changed for backward compat."""
        peer = _create_peer(client, admin_access_token)

        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock()
            mock_mgr.return_value = mock_manager

            client.delete(
                f"/api/v1/peers/{peer['peerId']}",
                headers=_auth_header(admin_access_token),
            )

            tunnel_events = [
                call for call in mock_manager.broadcast.call_args_list
                if call[0][0].get("type") == "tunnel.status_changed"
            ]
            assert len(tunnel_events) >= 1
            assert tunnel_events[0][0][0]["data"]["status"] == "down"

    def test_broadcast_failure_does_not_fail_mutation(self, client, admin_access_token):
        """Verify broadcast failure is best-effort and doesn't fail the API call."""
        with patch("backend.app.api.peers.get_monitoring_ws_manager") as mock_mgr:
            mock_manager = MagicMock()
            mock_manager.broadcast = AsyncMock(side_effect=Exception("ws error"))
            mock_mgr.return_value = mock_manager

            resp = client.post(
                "/api/v1/peers",
                headers=_auth_header(admin_access_token),
                json={
                    "name": "broadcast-fail-peer",
                    "remoteIp": "10.0.0.5",
                    "psk": "key",
                    "ikeVersion": "ikev2",
                },
            )
            # Mutation succeeds despite broadcast failure
            assert resp.status_code == 201
