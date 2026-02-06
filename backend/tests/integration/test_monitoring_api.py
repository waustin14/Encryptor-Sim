"""Integration tests for monitoring REST API endpoints (Story 5.5, Task 1).

Tests verify GET /api/v1/monitoring/tunnels and /interfaces endpoints
including auth, envelope shape, daemon IPC, and fallback behavior.
"""

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

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
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def admin_tokens(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert response.status_code == 200
    return response.json()["data"]


@pytest.fixture
def admin_access_token(admin_tokens):
    return admin_tokens["accessToken"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_peer(client, token, name="test-peer", remote_ip="10.1.1.100",
                 psk="super-secret-key", ike_version="ikev2", **kwargs):
    body = {
        "name": name,
        "remoteIp": remote_ip,
        "psk": psk,
        "ikeVersion": ike_version,
        **kwargs,
    }
    return client.post(
        "/api/v1/peers",
        headers=_auth_header(token),
        json=body,
    )


# ---------------------------------------------------------------------------
# Task 1.2: GET /api/v1/monitoring/tunnels
# ---------------------------------------------------------------------------


class TestGetTunnelTelemetry:
    """Tests for GET /api/v1/monitoring/tunnels (AC: #3, #5, #8)."""

    def test_requires_auth(self, client):
        """Verify monitoring tunnels endpoint requires JWT auth."""
        response = client.get("/api/v1/monitoring/tunnels")
        assert response.status_code in (401, 403)

    def test_returns_envelope_shape(self, client, admin_access_token, monkeypatch):
        """Verify response follows { data, meta } envelope."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)

    def test_returns_telemetry_for_peers(self, client, admin_access_token, monkeypatch):
        """Verify telemetry entries are returned per peer."""
        import backend.app.api.monitoring

        _create_peer(client, admin_access_token, name="peer-a", remote_ip="10.0.0.1")

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                "1": {
                    "status": "up",
                    "establishedSec": 120,
                    "bytesIn": 5000,
                    "bytesOut": 3000,
                    "packetsIn": 50,
                    "packetsOut": 30,
                },
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) >= 1
        entry = data[0]
        assert "peerId" in entry
        assert "peerName" in entry
        assert "status" in entry
        assert "establishedSec" in entry
        assert "bytesIn" in entry
        assert "bytesOut" in entry
        assert "packetsIn" in entry
        assert "packetsOut" in entry
        assert "isPassingTraffic" in entry
        assert "lastTrafficAt" in entry
        assert "timestamp" in entry

    def test_telemetry_schema_fields(self, client, admin_access_token, monkeypatch):
        """Verify telemetry entry has all required fields from story spec."""
        import backend.app.api.monitoring

        _create_peer(client, admin_access_token, name="schema-peer", remote_ip="10.0.0.2")

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                "1": {
                    "status": "up",
                    "establishedSec": 60,
                    "bytesIn": 100,
                    "bytesOut": 200,
                    "packetsIn": 5,
                    "packetsOut": 10,
                },
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        body = response.json()
        entry = body["data"][0]
        assert entry["status"] == "up"
        assert entry["establishedSec"] == 60
        assert entry["bytesIn"] == 100
        assert entry["bytesOut"] == 200
        assert entry["packetsIn"] == 5
        assert entry["packetsOut"] == 10

    def test_telemetry_passes_traffic_indicator_fields(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify telemetry includes isPassingTraffic and lastTrafficAt values."""
        import backend.app.api.monitoring

        create_resp = _create_peer(
            client,
            admin_access_token,
            name="traffic-fields-peer",
            remote_ip="10.0.0.9",
        )
        peer_id = create_resp.json()["data"]["peerId"]

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                str(peer_id): {
                    "status": "up",
                    "establishedSec": 30,
                    "bytesIn": 1024,
                    "bytesOut": 2048,
                    "packetsIn": 10,
                    "packetsOut": 20,
                    "isPassingTraffic": True,
                    "lastTrafficAt": "2026-02-06T12:34:56+00:00",
                },
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        entry = response.json()["data"][0]
        assert entry["isPassingTraffic"] is True
        assert entry["lastTrafficAt"] == "2026-02-06T12:34:56+00:00"

    def test_fallback_to_status_when_telemetry_fails(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify fallback to get_tunnel_status when telemetry unavailable (AC: #3)."""
        import backend.app.api.monitoring

        _create_peer(client, admin_access_token, name="fallback-peer", remote_ip="10.0.0.3")

        call_count = {"n": 0}

        def mock_send(command, payload=None):
            call_count["n"] += 1
            if command == "get_tunnel_telemetry":
                raise RuntimeError("telemetry unavailable")
            if command == "get_tunnel_status":
                return {"status": "ok", "result": {"1": "up"}}
            return {"status": "ok", "result": {}}

        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert "warning" in meta  # Should warn about fallback

    def test_daemon_unavailable_returns_200_with_warning(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify 200 with warning when daemon is completely unavailable (AC: #7)."""
        import backend.app.api.monitoring

        mock_send = MagicMock(side_effect=ConnectionError("daemon down"))
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta

    def test_meta_contains_count(self, client, admin_access_token, monkeypatch):
        """Verify meta.count reflects number of entries."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        meta = response.json()["meta"]
        assert "count" in meta

    def test_meta_contains_daemon_available(self, client, admin_access_token, monkeypatch):
        """Verify meta.daemonAvailable is present."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        meta = response.json()["meta"]
        assert "daemonAvailable" in meta

    def test_empty_response_with_no_peers(self, client, admin_access_token, monkeypatch):
        """Verify empty data when no peers exist."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/tunnels",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# Task 1.3: GET /api/v1/monitoring/interfaces
# ---------------------------------------------------------------------------


class TestGetInterfaceStats:
    """Tests for GET /api/v1/monitoring/interfaces (AC: #4, #5, #8)."""

    def test_requires_auth(self, client):
        """Verify monitoring interfaces endpoint requires JWT auth."""
        response = client.get("/api/v1/monitoring/interfaces")
        assert response.status_code in (401, 403)

    def test_returns_envelope_shape(self, client, admin_access_token, monkeypatch):
        """Verify response follows { data, meta } envelope."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)

    def test_returns_stats_per_interface(self, client, admin_access_token, monkeypatch):
        """Verify stats entries returned per interface."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                "CT": {
                    "bytesRx": 1000, "bytesTx": 2000,
                    "packetsRx": 10, "packetsTx": 20,
                    "errorsRx": 0, "errorsTx": 0,
                },
                "PT": {
                    "bytesRx": 3000, "bytesTx": 4000,
                    "packetsRx": 30, "packetsTx": 40,
                    "errorsRx": 1, "errorsTx": 2,
                },
                "MGMT": {
                    "bytesRx": 500, "bytesTx": 600,
                    "packetsRx": 5, "packetsTx": 6,
                    "errorsRx": 0, "errorsTx": 0,
                },
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3
        interfaces = {e["interface"] for e in data}
        assert interfaces == {"CT", "PT", "MGMT"}

    def test_interface_stats_schema_fields(self, client, admin_access_token, monkeypatch):
        """Verify interface stats entry has all required fields."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                "CT": {
                    "bytesRx": 1000, "bytesTx": 2000,
                    "packetsRx": 10, "packetsTx": 20,
                    "errorsRx": 0, "errorsTx": 0,
                },
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        entry = response.json()["data"][0]
        assert entry["interface"] == "CT"
        assert entry["bytesRx"] == 1000
        assert entry["bytesTx"] == 2000
        assert entry["packetsRx"] == 10
        assert entry["packetsTx"] == 20
        assert entry["errorsRx"] == 0
        assert entry["errorsTx"] == 0
        assert "timestamp" in entry

    def test_daemon_unavailable_returns_200_with_warning(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify 200 with warning when daemon unavailable (AC: #7)."""
        import backend.app.api.monitoring

        mock_send = MagicMock(side_effect=ConnectionError("daemon down"))
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta
        assert response.json()["data"] == []

    def test_meta_contains_count(self, client, admin_access_token, monkeypatch):
        """Verify meta.count reflects number of entries."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={
            "status": "ok",
            "result": {
                "CT": {"bytesRx": 0, "bytesTx": 0, "packetsRx": 0,
                        "packetsTx": 0, "errorsRx": 0, "errorsTx": 0},
            },
        })
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        meta = response.json()["meta"]
        assert meta["count"] == 1

    def test_meta_contains_daemon_available(self, client, admin_access_token, monkeypatch):
        """Verify meta.daemonAvailable is present."""
        import backend.app.api.monitoring

        mock_send = MagicMock(return_value={"status": "ok", "result": {}})
        monkeypatch.setattr(backend.app.api.monitoring, "send_command", mock_send)

        response = client.get(
            "/api/v1/monitoring/interfaces",
            headers=_auth_header(admin_access_token),
        )
        meta = response.json()["meta"]
        assert "daemonAvailable" in meta
        assert meta["daemonAvailable"] is True
