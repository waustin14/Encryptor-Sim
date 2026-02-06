"""Integration tests for automation write contract hardening (Story 5.5, Task 2).

Tests verify consistent { data, meta } envelopes, daemon metadata,
RFC 7807 instance values, and route delete normalization.
"""

import os
from unittest.mock import MagicMock

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


def _create_peer(client, token, name="auto-peer", remote_ip="10.1.1.100"):
    body = {
        "name": name,
        "remoteIp": remote_ip,
        "psk": "super-secret-key",
        "ikeVersion": "ikev2",
    }
    resp = client.post("/api/v1/peers", headers=_auth_header(token), json=body)
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


# ---------------------------------------------------------------------------
# 2.1: Envelope consistency across mutation endpoints
# ---------------------------------------------------------------------------


class TestEnvelopeConsistency:
    """Verify all mutation endpoints return { data, meta } envelopes (AC: #1, #5)."""

    def test_peer_create_envelope(self, client, admin_access_token):
        resp = client.post(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
            json={"name": "env-peer", "remoteIp": "10.0.0.1",
                  "psk": "key", "ikeVersion": "ikev2"},
        )
        body = resp.json()
        assert "data" in body and "meta" in body

    def test_peer_update_envelope(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        resp = client.put(
            f"/api/v1/peers/{peer['peerId']}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 45},
        )
        body = resp.json()
        assert "data" in body and "meta" in body

    def test_peer_delete_envelope(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        resp = client.delete(
            f"/api/v1/peers/{peer['peerId']}",
            headers=_auth_header(admin_access_token),
        )
        body = resp.json()
        assert "data" in body and "meta" in body

    def test_route_create_envelope(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        resp = client.post(
            "/api/v1/routes",
            headers=_auth_header(admin_access_token),
            json={"peerId": peer["peerId"], "destinationCidr": "10.0.0.0/8"},
        )
        body = resp.json()
        assert "data" in body and "meta" in body

    def test_route_update_envelope(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])
        resp = client.put(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
            json={"destinationCidr": "172.16.0.0/12"},
        )
        body = resp.json()
        assert "data" in body and "meta" in body

    def test_route_delete_envelope(self, client, admin_access_token):
        """Verify route delete returns { data, meta } envelope (Story 5.5 2.2)."""
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])
        resp = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body and "meta" in body
        assert body["data"]["routeId"] == route["routeId"]

    def test_interface_configure_envelope(self, client, admin_access_token, monkeypatch):
        import backend.app.api.interfaces

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {"status": "success", "isolation": {"status": "pass"}},
        })
        monkeypatch.setattr(backend.app.api.interfaces, "send_command", mock_send)

        resp = client.post(
            "/api/v1/interfaces/ct/configure",
            headers=_auth_header(admin_access_token),
            json={"ipAddress": "10.0.0.1", "netmask": "255.255.255.0", "gateway": "10.0.0.254"},
        )
        body = resp.json()
        assert "data" in body and "meta" in body


# ---------------------------------------------------------------------------
# 2.2: Route delete returns machine-readable envelope
# ---------------------------------------------------------------------------


class TestRouteDeleteNormalized:
    """Verify route delete is machine-readable for automation (AC: #1, #5, #7)."""

    def test_route_delete_returns_deleted_route_data(self, client, admin_access_token):
        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"], "10.0.0.0/8")
        resp = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["routeId"] == route["routeId"]
        assert data["destinationCidr"] == "10.0.0.0/8"
        assert data["peerName"] == "auto-peer"

    def test_route_delete_daemon_unavailable_returns_warning(
        self, client, admin_access_token, monkeypatch
    ):
        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        mock_send = MagicMock(side_effect=ConnectionError("daemon down"))
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        resp = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta


# ---------------------------------------------------------------------------
# 2.3: meta.daemonAvailable and meta.warning across writes
# ---------------------------------------------------------------------------


class TestDaemonMetadata:
    """Verify daemon metadata in mutation responses (AC: #7)."""

    def test_peer_create_daemon_available(self, client, admin_access_token, monkeypatch):
        import backend.app.api.peers

        mock_send = MagicMock(return_value={"status": "ok", "result": {"status": "success"}})
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        resp = client.post(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
            json={"name": "daemon-peer", "remoteIp": "10.0.0.1",
                  "psk": "key", "ikeVersion": "ikev2"},
        )
        assert resp.json()["meta"]["daemonAvailable"] is True

    def test_peer_create_daemon_unavailable(self, client, admin_access_token, monkeypatch):
        import backend.app.api.peers

        mock_send = MagicMock(side_effect=ConnectionError("daemon down"))
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        resp = client.post(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
            json={"name": "daemon-down-peer", "remoteIp": "10.0.0.2",
                  "psk": "key", "ikeVersion": "ikev2"},
        )
        meta = resp.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta

    def test_route_create_daemon_available(self, client, admin_access_token, monkeypatch):
        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token)

        mock_send = MagicMock(return_value={"status": "ok", "result": {"status": "success"}})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        resp = client.post(
            "/api/v1/routes",
            headers=_auth_header(admin_access_token),
            json={"peerId": peer["peerId"], "destinationCidr": "10.0.0.0/8"},
        )
        assert resp.json()["meta"]["daemonAvailable"] is True

    def test_route_delete_daemon_available(self, client, admin_access_token, monkeypatch):
        import backend.app.api.routes

        peer = _create_peer(client, admin_access_token)
        route = _create_route(client, admin_access_token, peer["peerId"])

        mock_send = MagicMock(return_value={"status": "ok", "result": {"status": "success"}})
        monkeypatch.setattr(backend.app.api.routes, "send_command", mock_send)

        resp = client.delete(
            f"/api/v1/routes/{route['routeId']}",
            headers=_auth_header(admin_access_token),
        )
        assert resp.json()["meta"]["daemonAvailable"] is True


# ---------------------------------------------------------------------------
# 2.4: RFC 7807 instance values
# ---------------------------------------------------------------------------


class TestRFC7807InstanceValues:
    """Verify RFC 7807 instance values are correct across endpoints (AC: #5)."""

    def test_peer_not_found_instance(self, client, admin_access_token):
        resp = client.get("/api/v1/peers/99999", headers=_auth_header(admin_access_token))
        assert resp.status_code == 404
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/peers/99999"

    def test_route_not_found_instance(self, client, admin_access_token):
        resp = client.get("/api/v1/routes/99999", headers=_auth_header(admin_access_token))
        assert resp.status_code == 404
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/routes/99999"

    def test_route_delete_not_found_instance(self, client, admin_access_token):
        resp = client.delete("/api/v1/routes/99999", headers=_auth_header(admin_access_token))
        assert resp.status_code == 404
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/routes/99999"

    def test_interface_not_found_instance(self, client, admin_access_token):
        resp = client.get("/api/v1/interfaces/xyz", headers=_auth_header(admin_access_token))
        assert resp.status_code == 404
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/interfaces/xyz"

    def test_peer_validation_instance(self, client, admin_access_token):
        resp = client.post(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
            json={"name": "bad", "remoteIp": "999.999.999.999",
                  "psk": "k", "ikeVersion": "ikev2"},
        )
        assert resp.status_code == 422
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/peers"

    def test_route_peer_not_found_instance(self, client, admin_access_token):
        resp = client.post(
            "/api/v1/routes",
            headers=_auth_header(admin_access_token),
            json={"peerId": 99999, "destinationCidr": "10.0.0.0/8"},
        )
        assert resp.status_code == 404
        error = resp.json()["detail"]
        assert error["instance"] == "/api/v1/routes"
