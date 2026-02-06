"""Integration tests for route deletion (Story 4.5).

Tests verify DELETE /api/v1/routes/{routeId} endpoint, service logic,
daemon IPC updates, and edge cases (last route, peer isolation).
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture(autouse=True)
def _clean_routes_and_peers():
    """Remove all routes and peers before each test for isolation."""
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


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_peer(client, token, name="test-peer", remote_ip="10.1.1.100"):
    """Helper to create a peer and return the response data."""
    body = {
        "name": name,
        "remoteIp": remote_ip,
        "psk": "super-secret-key",
        "ikeVersion": "ikev2",
    }
    response = client.post(
        "/api/v1/peers",
        headers=_auth_header(token),
        json=body,
    )
    assert response.status_code == 201
    return response.json()["data"]


def _create_route(client, token, peer_id, cidr="192.168.1.0/24"):
    """Helper to create a route and return the response."""
    response = client.post(
        "/api/v1/routes",
        headers=_auth_header(token),
        json={"peerId": peer_id, "destinationCidr": cidr},
    )
    assert response.status_code == 201
    return response.json()["data"]


# ---------------------------------------------------------------------------
# DELETE /api/v1/routes/{routeId} - Delete route (AC: #1, #2, #3)
# ---------------------------------------------------------------------------


class TestDeleteRoute:
    """Tests for DELETE /api/v1/routes/{routeId} (AC: #1, #2, #3)."""

    def test_delete_route_succeeds(self, client, admin_access_token):
        """Verify DELETE /api/v1/routes/{routeId} returns 200 with envelope (AC: #1)."""
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        response = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["routeId"] == route["routeId"]

    def test_delete_nonexistent_route_returns_404(self, client, admin_access_token):
        """Verify deleting non-existent route returns 404 (AC: #3)."""
        response = client.delete(
            "/api/v1/routes/99999",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404
        assert "not found" in error["detail"].lower()

    def test_delete_route_removes_from_database(self, client, admin_access_token):
        """Verify route is removed from database after deletion (AC: #1)."""
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        # Verify route no longer exists
        response = client.get(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404

    def test_delete_route_requires_auth(self, client):
        """Verify DELETE /api/v1/routes/{routeId} requires authentication."""
        response = client.delete("/api/v1/routes/1")
        assert response.status_code in (401, 403)

    def test_delete_route_rfc7807_error_format(self, client, admin_access_token):
        """Verify 404 error follows RFC 7807 format (AC: #3)."""
        response = client.delete(
            "/api/v1/routes/99999",
            headers=_auth_header(admin_access_token),
        )
        error = response.json()["detail"]
        assert error["type"] == "about:blank"
        assert error["title"] == "Not Found"
        assert error["status"] == 404
        assert "detail" in error
        assert "instance" in error

    def test_delete_route_returns_envelope_with_meta(self, client, admin_access_token):
        """Verify delete response returns { data, meta } envelope with daemon metadata."""
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        response = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["destinationCidr"] == route["destinationCidr"]


# ---------------------------------------------------------------------------
# Traffic selector updates after deletion (AC: #4, #5, #6, #7)
# ---------------------------------------------------------------------------


class TestDeleteRouteTrafficSelectors:
    """Tests for traffic selector updates after route deletion (AC: #4-7)."""

    def test_delete_route_updates_peer_traffic_selectors(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify daemon IPC called with updated routes after deletion (AC: #4)."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token, name="ts-peer")
        _create_route(client, admin_access_token, peer["peerId"], "192.168.1.0/24")
        route2 = _create_route(client, admin_access_token, peer["peerId"], "10.0.0.0/8")

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        client.delete(
            f"/api/v1/routes/{route2['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        update_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "update_routes"
        ]
        assert len(update_calls) == 1
        assert update_calls[0][0][1]["peer_name"] == "ts-peer"
        # Only the first route should remain
        assert len(update_calls[0][0][1]["routes"]) == 1
        assert update_calls[0][0][1]["routes"][0]["destination_cidr"] == "192.168.1.0/24"

    def test_delete_last_route_sends_empty_routes(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify deleting last route sends empty routes list (AC: #5, #6)."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token, name="last-route-peer")
        route = _create_route(client, admin_access_token, peer["peerId"], "192.168.1.0/24")

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        update_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "update_routes"
        ]
        assert len(update_calls) == 1
        assert update_calls[0][0][1]["peer_name"] == "last-route-peer"
        assert update_calls[0][0][1]["routes"] == []

    def test_delete_last_route_leaves_peer_with_no_routes(
        self, client, admin_access_token
    ):
        """Verify deleting last route leaves peer with empty route list (AC: #6)."""
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        # Verify peer has no routes
        response = client.get(
            f"/api/v1/routes?peerId={peer['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 0

    def test_delete_route_does_not_affect_other_peers(
        self, client, admin_access_token
    ):
        """Verify deleting route for peer A doesn't affect peer B (AC: #7)."""
        peer_a = _create_peer(
            client, admin_access_token, name="peer-a", remote_ip="10.0.0.1"
        )
        peer_b = _create_peer(
            client, admin_access_token, name="peer-b", remote_ip="10.0.0.2"
        )

        route_a = _create_route(
            client, admin_access_token, peer_a["peerId"], "192.168.1.0/24"
        )
        route_b = _create_route(
            client, admin_access_token, peer_b["peerId"], "10.0.0.0/8"
        )

        # Delete route for peer A
        client.delete(
            f"/api/v1/routes/{route_a['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        # Verify peer B route still exists
        response = client.get(
            f"/api/v1/routes/{route_b['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["routeId"] == route_b["routeId"]

    def test_delete_route_succeeds_when_daemon_unavailable(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify route deletion succeeds even when daemon IPC fails (AC: #4)."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        mock_send = MagicMock(side_effect=ConnectionError("Daemon not running"))
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        response = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200

    def test_delete_one_of_multiple_routes_updates_correctly(
        self, client, admin_access_token
    ):
        """Verify remaining routes persist after deleting one (AC: #5)."""
        peer = _create_peer(client, admin_access_token)
        route1 = _create_route(
            client, admin_access_token, peer["peerId"], "192.168.1.0/24"
        )
        route2 = _create_route(
            client, admin_access_token, peer["peerId"], "10.0.0.0/8"
        )
        _create_route(
            client, admin_access_token, peer["peerId"], "172.16.0.0/12"
        )

        # Delete route2
        client.delete(
            f"/api/v1/routes/{route2['routeId']}",
            headers=_auth_header(admin_access_token),
        )

        # Verify remaining routes
        response = client.get(
            f"/api/v1/routes?peerId={peer['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        routes = response.json()["data"]
        assert len(routes) == 2
        cidrs = [r["destinationCidr"] for r in routes]
        assert "192.168.1.0/24" in cidrs
        assert "172.16.0.0/12" in cidrs
        assert "10.0.0.0/8" not in cidrs
