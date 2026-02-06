"""Integration tests for peer tunnel initiation (Story 5.2, Task 3)."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.peer import Peer
from backend.app.services.psk_crypto import encrypt_psk
from backend.main import app


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
    """Test client for the API."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for API requests."""
    # Login as default admin
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    """Get a database session for setup/teardown."""
    from backend.app.config import get_settings
    from backend.app.db.session import create_session_factory

    settings = get_settings()
    factory = create_session_factory(settings.database_url)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def ready_peer(db_session: Session) -> Peer:
    """Create a ready peer in the database."""
    peer = Peer(
        name="test-ready-peer",
        remoteIp="10.1.1.100",
        psk=encrypt_psk("secret123"),
        ikeVersion="ikev2",
        dpdAction="restart",
        dpdDelay=30,
        dpdTimeout=150,
        rekeyTime=3600,
    )
    db_session.add(peer)
    db_session.commit()
    db_session.refresh(peer)
    return peer


@pytest.fixture
def incomplete_peer(db_session: Session) -> Peer:
    """Create an incomplete peer (invalid IP)."""
    peer = Peer(
        name="test-incomplete-peer",
        remoteIp="not-an-ip",
        psk=encrypt_psk("secret456"),
        ikeVersion="ikev2",
    )
    db_session.add(peer)
    db_session.commit()
    db_session.refresh(peer)
    return peer


class TestInitiatePeerSuccess:
    """Tests for successful peer tunnel initiation."""

    def test_initiate_ready_peer_succeeds(
        self, client, auth_headers, ready_peer, db_session
    ):
        """Verify initiating a ready peer returns success (AC: #1, #6)."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {
                "status": "ok",
                "result": {
                    "status": "success",
                    "message": "Tunnel initiated for peer test-ready-peer",
                },
            }

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify envelope structure (AC: #6)
            assert "data" in data
            assert "meta" in data

            # Verify data contains peer info
            assert data["data"]["peerId"] == ready_peer.peerId
            assert data["data"]["name"] == "test-ready-peer"

            # Verify meta contains daemon status and initiation result (AC: #6)
            assert data["meta"]["daemonAvailable"] is True
            assert data["meta"]["initiationStatus"] == "success"
            assert "initiated" in data["meta"]["initiationMessage"].lower()

            # Verify daemon was called with correct payload (AC: #3)
            mock_send.assert_called_once_with(
                "initiate_peer", {"name": "test-ready-peer"}
            )

    def test_initiate_idempotent_already_up(
        self, client, auth_headers, ready_peer, db_session
    ):
        """Verify initiation is idempotent when tunnel already up (AC: #10)."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {
                "status": "ok",
                "result": {
                    "status": "success",
                    "message": "Tunnel already established for peer test-ready-peer",
                },
            }

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["meta"]["initiationStatus"] == "success"
            assert "already" in data["meta"]["initiationMessage"].lower()

    def test_initiate_emits_negotiating_event(
        self, client, auth_headers, ready_peer
    ):
        """Verify initiation broadcasts negotiating status (AC: #9)."""
        manager = MagicMock()
        manager.broadcast = AsyncMock()
        with patch("backend.app.api.peers.send_command") as mock_send, patch(
            "backend.app.api.peers.get_monitoring_ws_manager"
        ) as mock_manager:
            mock_send.return_value = {
                "status": "ok",
                "result": {
                    "status": "success",
                    "message": "Tunnel initiated for peer test-ready-peer",
                },
            }
            mock_manager.return_value = manager

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 200
            manager.broadcast.assert_awaited_once()
            event = manager.broadcast.await_args[0][0]
            assert event["type"] == "tunnel.status_changed"
            assert event["data"]["status"] == "negotiating"
            assert event["data"]["peerId"] == ready_peer.peerId


class TestInitiatePeerErrors:
    """Tests for peer tunnel initiation error cases."""

    def test_initiate_missing_peer_returns_404(self, client, auth_headers):
        """Verify initiating non-existent peer returns 404 (AC: #7, Task 3.5)."""
        response = client.post(
            "/api/v1/peers/99999/initiate",
            headers=auth_headers,
        )

        assert response.status_code == 404
        detail = response.json()["detail"]

        # Verify RFC 7807 structure
        assert detail["status"] == 404
        assert detail["title"] == "Not Found"
        assert "99999" in detail["detail"]
        assert "/api/v1/peers/99999/initiate" in detail["instance"]

    def test_initiate_incomplete_peer_returns_409(
        self, client, auth_headers, incomplete_peer
    ):
        """Verify initiating incomplete peer returns 409 (AC: #7, Task 3.2, 3.5)."""
        # Verify peer is incomplete
        assert incomplete_peer.operationalStatus == "incomplete"

        response = client.post(
            f"/api/v1/peers/{incomplete_peer.peerId}/initiate",
            headers=auth_headers,
        )

        assert response.status_code == 409
        detail = response.json()["detail"]

        # Verify RFC 7807 structure
        assert detail["status"] == 409
        assert detail["title"] == "Conflict"
        assert "not ready" in detail["detail"].lower()
        assert "incomplete" in detail["detail"].lower()

    def test_initiate_daemon_unavailable_returns_503(
        self, client, auth_headers, ready_peer
    ):
        """Verify daemon unavailability returns 503 (AC: #7, Task 3.5)."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.side_effect = ConnectionError("Daemon not reachable")

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 503
            detail = response.json()["detail"]

            # Verify RFC 7807 structure
            assert detail["status"] == 503
        assert detail["title"] == "Service Unavailable"
        assert "daemon" in detail["detail"].lower()

    def test_initiate_daemon_warning_returns_503(
        self, client, auth_headers, ready_peer
    ):
        """Verify daemon warning response returns RFC 7807 (AC: #7)."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {
                "status": "ok",
                "result": {
                    "status": "warning",
                    "message": "swanctl not available, skipping initiation",
                },
            }

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 503
            detail = response.json()["detail"]
            assert detail["status"] == 503
            assert detail["title"] == "Service Unavailable"
            assert "swanctl" in detail["detail"].lower()

    def test_initiate_daemon_returns_error_status(
        self, client, auth_headers, ready_peer
    ):
        """Verify daemon error status is surfaced in meta (AC: #6)."""
        with patch("backend.app.api.peers.send_command") as mock_send:
            mock_send.return_value = {
                "status": "ok",
                "result": {
                    "status": "error",
                    "message": "Tunnel initiation failed for peer test-ready-peer",
                },
            }

            response = client.post(
                f"/api/v1/peers/{ready_peer.peerId}/initiate",
                headers=auth_headers,
            )

            assert response.status_code == 200
            meta = response.json()["meta"]
            assert meta["daemonAvailable"] is True
            assert meta["initiationStatus"] == "error"
            assert "failed" in meta["initiationMessage"].lower()

    def test_initiate_unauthorized_returns_401(self, client, ready_peer):
        """Verify initiation without auth returns 401 (Task 3.6)."""
        response = client.post(f"/api/v1/peers/{ready_peer.peerId}/initiate")

        assert response.status_code == 401
