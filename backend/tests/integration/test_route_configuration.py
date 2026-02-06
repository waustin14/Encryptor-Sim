"""Integration tests for route configuration (Story 4.4).

Tests verify route API endpoints, CIDR validation, peer FK constraints,
and route CRUD operations.
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
    """Helper to create a peer and return the response."""
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
    return client.post(
        "/api/v1/routes",
        headers=_auth_header(token),
        json={"peerId": peer_id, "destinationCidr": cidr},
    )


# ---------------------------------------------------------------------------
# POST /api/v1/routes - Create route (AC: #1)
# ---------------------------------------------------------------------------


class TestCreateRoute:
    """Tests for POST /api/v1/routes (AC: #1, #5, #6)."""

    def test_create_route_succeeds(self, client, admin_access_token):
        """Verify POST /api/v1/routes creates route successfully (AC: #1)."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(client, admin_access_token, peer["peerId"])

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["peerId"] == peer["peerId"]
        assert data["destinationCidr"] == "192.168.1.0/24"
        assert "routeId" in data
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_create_route_returns_201(self, client, admin_access_token):
        """Verify create route returns 201 Created."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(client, admin_access_token, peer["peerId"])
        assert response.status_code == 201

    def test_create_route_returns_envelope(self, client, admin_access_token):
        """Verify create route returns { data, meta } envelope."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(client, admin_access_token, peer["peerId"])
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_create_route_includes_peer_name(self, client, admin_access_token):
        """Verify route response includes peer name."""
        peer = _create_peer(client, admin_access_token, name="site-a")
        response = _create_route(client, admin_access_token, peer["peerId"])
        data = response.json()["data"]
        assert data["peerName"] == "site-a"

    def test_create_route_normalizes_cidr(self, client, admin_access_token):
        """Verify CIDR is normalized (host bits cleared)."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(
            client, admin_access_token, peer["peerId"], cidr="192.168.1.5/24"
        )
        assert response.status_code == 201
        assert response.json()["data"]["destinationCidr"] == "192.168.1.0/24"

    def test_create_route_with_invalid_cidr_returns_422(self, client, admin_access_token):
        """Verify invalid CIDR format returns 422 (AC: #5)."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(
            client, admin_access_token, peer["peerId"], cidr="192.168.1.0/33"
        )
        assert response.status_code == 422

    def test_create_route_with_nonexistent_peer_returns_404(self, client, admin_access_token):
        """Verify non-existent peer returns 404 (AC: #6)."""
        response = _create_route(client, admin_access_token, 99999)
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404
        assert "peer" in error["detail"].lower()

    def test_create_route_requires_auth(self, client):
        """Verify POST /api/v1/routes requires authentication."""
        response = client.post(
            "/api/v1/routes",
            json={"peerId": 1, "destinationCidr": "192.168.1.0/24"},
        )
        assert response.status_code in (401, 403)

    def test_create_route_with_non_string_cidr_returns_422(self, client, admin_access_token):
        """Verify non-CIDR string returns 422."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(
            client, admin_access_token, peer["peerId"], cidr="not-a-cidr"
        )
        assert response.status_code == 422

    def test_create_route_slash_0_succeeds(self, client, admin_access_token):
        """Verify /0 CIDR is valid."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(
            client, admin_access_token, peer["peerId"], cidr="0.0.0.0/0"
        )
        assert response.status_code == 201
        assert response.json()["data"]["destinationCidr"] == "0.0.0.0/0"

    def test_create_route_slash_32_succeeds(self, client, admin_access_token):
        """Verify /32 CIDR (single host) is valid."""
        peer = _create_peer(client, admin_access_token)
        response = _create_route(
            client, admin_access_token, peer["peerId"], cidr="10.0.0.1/32"
        )
        assert response.status_code == 201
        assert response.json()["data"]["destinationCidr"] == "10.0.0.1/32"


# ---------------------------------------------------------------------------
# GET /api/v1/routes - List routes (AC: #2)
# ---------------------------------------------------------------------------


class TestListRoutes:
    """Tests for GET /api/v1/routes (AC: #2)."""

    def test_list_routes_empty(self, client, admin_access_token):
        """Verify GET /api/v1/routes returns empty list when no routes exist."""
        response = client.get(
            "/api/v1/routes", headers=_auth_header(admin_access_token)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert "meta" in body
        assert body["meta"]["count"] == 0

    def test_list_routes_returns_all(self, client, admin_access_token):
        """Verify GET /api/v1/routes returns all created routes."""
        peer = _create_peer(client, admin_access_token)
        _create_route(client, admin_access_token, peer["peerId"], "192.168.1.0/24")
        _create_route(client, admin_access_token, peer["peerId"], "10.0.0.0/8")

        response = client.get(
            "/api/v1/routes", headers=_auth_header(admin_access_token)
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 2
        assert response.json()["meta"]["count"] == 2

    def test_list_routes_filtered_by_peer(self, client, admin_access_token):
        """Verify GET /api/v1/routes?peerId=X filters routes (AC: #2)."""
        peer1 = _create_peer(client, admin_access_token, name="peer-1", remote_ip="10.0.0.1")
        peer2 = _create_peer(client, admin_access_token, name="peer-2", remote_ip="10.0.0.2")

        _create_route(client, admin_access_token, peer1["peerId"], "192.168.1.0/24")
        _create_route(client, admin_access_token, peer2["peerId"], "10.0.0.0/8")

        response = client.get(
            f"/api/v1/routes?peerId={peer1['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        routes = response.json()["data"]
        assert len(routes) == 1
        assert routes[0]["peerId"] == peer1["peerId"]
        assert routes[0]["destinationCidr"] == "192.168.1.0/24"

    def test_list_routes_requires_auth(self, client):
        """Verify GET /api/v1/routes requires authentication."""
        response = client.get("/api/v1/routes")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v1/routes/{routeId} - Get single route
# ---------------------------------------------------------------------------


class TestGetRoute:
    """Tests for GET /api/v1/routes/{routeId}."""

    def test_get_route_by_id(self, client, admin_access_token):
        """Verify GET /api/v1/routes/{routeId} returns specific route."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.get(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["routeId"] == route_id
        assert data["destinationCidr"] == "192.168.1.0/24"

    def test_get_route_returns_envelope(self, client, admin_access_token):
        """Verify GET response follows { data, meta } envelope."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.get(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_get_nonexistent_route_returns_404(self, client, admin_access_token):
        """Verify GET for nonexistent route returns 404."""
        response = client.get(
            "/api/v1/routes/99999",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404

    def test_get_route_includes_peer_name(self, client, admin_access_token):
        """Verify GET route includes peer name."""
        peer = _create_peer(client, admin_access_token, name="named-peer")
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.get(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.json()["data"]["peerName"] == "named-peer"

    def test_get_route_requires_auth(self, client):
        """Verify GET /api/v1/routes/{routeId} requires authentication."""
        response = client.get("/api/v1/routes/1")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/v1/routes/{routeId} - Update route (AC: #3)
# ---------------------------------------------------------------------------


class TestUpdateRoute:
    """Tests for PUT /api/v1/routes/{routeId} (AC: #3)."""

    def test_update_route_succeeds(self, client, admin_access_token):
        """Verify PUT /api/v1/routes/{routeId} updates route (AC: #3)."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.put(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "10.0.0.0/8"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["routeId"] == route_id
        assert data["destinationCidr"] == "10.0.0.0/8"

    def test_update_route_normalizes_cidr(self, client, admin_access_token):
        """Verify update normalizes CIDR."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.put(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "172.16.5.3/12"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["destinationCidr"] == "172.16.0.0/12"

    def test_update_route_invalid_cidr_returns_422(self, client, admin_access_token):
        """Verify update with invalid CIDR returns 422."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.put(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "999.999.999.999/24"},
        )
        assert response.status_code == 422

    def test_update_nonexistent_route_returns_404(self, client, admin_access_token):
        """Verify PUT for nonexistent route returns 404."""
        response = client.put(
            "/api/v1/routes/99999",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "10.0.0.0/8"},
        )
        assert response.status_code == 404

    def test_update_route_returns_envelope(self, client, admin_access_token):
        """Verify update returns { data, meta } envelope."""
        peer = _create_peer(client, admin_access_token)
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        response = client.put(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "10.0.0.0/8"},
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_update_route_requires_auth(self, client):
        """Verify PUT /api/v1/routes/{routeId} requires authentication."""
        response = client.put(
            "/api/v1/routes/1",
            json={"destinationCidr": "10.0.0.0/8"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Multiple routes per peer (AC: #8)
# ---------------------------------------------------------------------------


class TestMultipleRoutes:
    """Tests for multiple routes per peer (AC: #8)."""

    def test_multiple_routes_per_peer_allowed(self, client, admin_access_token):
        """Verify multiple routes can be associated with one peer (AC: #8)."""
        peer = _create_peer(client, admin_access_token)
        cidrs = ["192.168.1.0/24", "192.168.2.0/24", "10.0.0.0/8"]

        for cidr in cidrs:
            response = _create_route(client, admin_access_token, peer["peerId"], cidr)
            assert response.status_code == 201

        # Verify all routes exist for peer
        response = client.get(
            f"/api/v1/routes?peerId={peer['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        routes = response.json()["data"]
        route_cidrs = [r["destinationCidr"] for r in routes]
        assert all(cidr in route_cidrs for cidr in cidrs)

    def test_routes_from_different_peers_separate(self, client, admin_access_token):
        """Verify routes from different peers are correctly separated."""
        peer1 = _create_peer(client, admin_access_token, name="peer-1", remote_ip="10.0.0.1")
        peer2 = _create_peer(client, admin_access_token, name="peer-2", remote_ip="10.0.0.2")

        _create_route(client, admin_access_token, peer1["peerId"], "192.168.1.0/24")
        _create_route(client, admin_access_token, peer1["peerId"], "192.168.2.0/24")
        _create_route(client, admin_access_token, peer2["peerId"], "10.0.0.0/8")

        # Filter peer 1
        response = client.get(
            f"/api/v1/routes?peerId={peer1['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        assert len(response.json()["data"]) == 2

        # Filter peer 2
        response = client.get(
            f"/api/v1/routes?peerId={peer2['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        assert len(response.json()["data"]) == 1


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestRoutePersistence:
    """Tests for route persistence."""

    def test_route_persists_across_api_restart(self, client, admin_access_token):
        """Verify route persists after restarting TestClient."""
        peer = _create_peer(client, admin_access_token, name="persist-peer")
        _create_route(client, admin_access_token, peer["peerId"], "192.168.1.0/24")

        from backend.main import app

        new_client = TestClient(app)
        login_resp = new_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        new_token = login_resp.json()["data"]["accessToken"]

        response = new_client.get(
            "/api/v1/routes",
            headers=_auth_header(new_token),
        )
        assert response.status_code == 200
        cidrs = [r["destinationCidr"] for r in response.json()["data"]]
        assert "192.168.1.0/24" in cidrs


# ---------------------------------------------------------------------------
# Daemon IPC tests (AC: #7)
# ---------------------------------------------------------------------------


class TestDaemonIPC:
    """Tests for daemon IPC route operations (AC: #7)."""

    def test_create_route_calls_daemon(self, client, admin_access_token, monkeypatch):
        """Verify route creation calls daemon update_routes (AC: #7)."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        peer = _create_peer(client, admin_access_token, name="daemon-test-peer")
        _create_route(client, admin_access_token, peer["peerId"], "192.168.1.0/24")

        update_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "update_routes"
        ]
        assert len(update_calls) == 1
        assert update_calls[0][0][1]["peer_name"] == "daemon-test-peer"
        assert len(update_calls[0][0][1]["routes"]) == 1
        assert update_calls[0][0][1]["routes"][0]["destination_cidr"] == "192.168.1.0/24"

    def test_create_route_succeeds_when_daemon_unavailable(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify route creation succeeds even when daemon IPC fails."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        mock_send = MagicMock(side_effect=ConnectionError("Daemon not running"))
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        peer = _create_peer(client, admin_access_token)
        response = _create_route(client, admin_access_token, peer["peerId"])

        assert response.status_code == 201
        meta = response.json()["meta"]
        assert meta["daemonAvailable"] is False

    def test_update_route_calls_daemon(self, client, admin_access_token, monkeypatch):
        """Verify route update calls daemon update_routes."""
        from unittest.mock import MagicMock

        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token, name="daemon-update-peer")
        create_resp = _create_route(client, admin_access_token, peer["peerId"])
        route_id = create_resp.json()["data"]["routeId"]

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        client.put(
            f"/api/v1/routes/{route_id}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "10.0.0.0/8"},
        )

        update_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "update_routes"
        ]
        assert len(update_calls) == 1


# ---------------------------------------------------------------------------
# RFC 7807 error format tests
# ---------------------------------------------------------------------------


class TestRFC7807Errors:
    """Tests for RFC 7807 error format compliance."""

    def test_404_error_format(self, client, admin_access_token):
        """Verify 404 errors follow RFC 7807 format."""
        response = _create_route(client, admin_access_token, 99999)
        error = response.json()["detail"]
        assert "type" in error
        assert "title" in error
        assert "status" in error
        assert "detail" in error
        assert "instance" in error

    def test_get_nonexistent_route_rfc7807(self, client, admin_access_token):
        """Verify GET 404 follows RFC 7807."""
        response = client.get(
            "/api/v1/routes/99999",
            headers=_auth_header(admin_access_token),
        )
        error = response.json()["detail"]
        assert error["type"] == "about:blank"
        assert error["title"] == "Not Found"
        assert error["status"] == 404
