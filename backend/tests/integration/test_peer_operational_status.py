"""Integration tests for peer operational status (Story 4.6).

Tests verify that operationalStatus is computed and returned
in all peer API responses.
"""

import os

import pytest
from fastapi.testclient import TestClient

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
def admin_access_token(client):
    """Login as admin and return access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert response.status_code == 200
    return response.json()["data"]["accessToken"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_peer(client, token, name="test-peer", remote_ip="10.1.1.100",
                 psk="super-secret-key", ike_version="ikev2", **kwargs):
    """Helper to create a peer."""
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


class TestPeerOperationalStatusInResponses:
    """Tests verifying operationalStatus appears in API responses (AC: #1, #3)."""

    def test_create_peer_returns_operational_status(self, client, admin_access_token):
        """Verify POST /api/v1/peers includes operationalStatus in response (AC: #3)."""
        response = _create_peer(client, admin_access_token, name="status-create")
        assert response.status_code == 201
        data = response.json()["data"]
        assert "operationalStatus" in data
        assert data["operationalStatus"] in ("ready", "incomplete")

    def test_get_peer_returns_operational_status(self, client, admin_access_token):
        """Verify GET /api/v1/peers/{peerId} includes operationalStatus (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="status-get")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "operationalStatus" in data
        assert data["operationalStatus"] in ("ready", "incomplete")

    def test_list_peers_returns_operational_status(self, client, admin_access_token):
        """Verify GET /api/v1/peers includes operationalStatus for each peer (AC: #3)."""
        _create_peer(client, admin_access_token, name="status-list-1", remote_ip="10.0.0.1")
        _create_peer(client, admin_access_token, name="status-list-2", remote_ip="10.0.0.2")

        response = client.get(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        peers = response.json()["data"]
        assert len(peers) >= 2
        for peer in peers:
            assert "operationalStatus" in peer
            assert peer["operationalStatus"] in ("ready", "incomplete")

    def test_update_peer_returns_operational_status(self, client, admin_access_token):
        """Verify PUT /api/v1/peers/{peerId} includes operationalStatus (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="status-update")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 45},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "operationalStatus" in data
        assert data["operationalStatus"] in ("ready", "incomplete")


class TestPeerOperationalStatusReady:
    """Tests verifying 'ready' status for valid peers (AC: #1, #4)."""

    def test_peer_with_all_required_fields_is_ready(self, client, admin_access_token):
        """Verify peer with all required fields has 'ready' status (AC: #1, #4)."""
        response = _create_peer(
            client, admin_access_token,
            name="complete-peer",
            remote_ip="10.5.5.5",
            psk="secure-key-value",
            ike_version="ikev2",
        )
        assert response.status_code == 201
        assert response.json()["data"]["operationalStatus"] == "ready"

    def test_peer_with_ikev1_is_ready(self, client, admin_access_token):
        """Verify peer with ikev1 has 'ready' status (AC: #4)."""
        response = _create_peer(
            client, admin_access_token,
            name="ikev1-peer",
            ike_version="ikev1",
        )
        assert response.status_code == 201
        assert response.json()["data"]["operationalStatus"] == "ready"

    def test_peer_with_all_optional_fields_is_ready(self, client, admin_access_token):
        """Verify peer with all fields (including optional) has 'ready' status."""
        response = _create_peer(
            client, admin_access_token,
            name="full-config-peer",
            remote_ip="10.2.2.200",
            ike_version="ikev2",
            dpdAction="hold",
            dpdDelay=45,
            dpdTimeout=200,
            rekeyTime=7200,
        )
        assert response.status_code == 201
        assert response.json()["data"]["operationalStatus"] == "ready"


class TestPeerOperationalStatusComputed:
    """Tests verifying operationalStatus is computed on every read (AC: #5, #6)."""

    def test_status_computed_without_daemon_calls(self, client, admin_access_token, monkeypatch):
        """Verify operationalStatus is computed without daemon IPC (AC: #5)."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        mock_send = MagicMock(side_effect=ConnectionError("Daemon down"))
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        response = _create_peer(client, admin_access_token, name="no-daemon-peer")
        assert response.status_code == 201
        assert response.json()["data"]["operationalStatus"] == "ready"

    def test_status_updates_when_peer_is_modified(self, client, admin_access_token):
        """Verify operationalStatus reflects current state after update (AC: #6)."""
        create_resp = _create_peer(
            client, admin_access_token,
            name="update-status-peer",
            remote_ip="10.1.1.1",
        )
        peer_id = create_resp.json()["data"]["peerId"]
        assert create_resp.json()["data"]["operationalStatus"] == "ready"

        # Update DPD params (peer should remain ready)
        update_resp = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 60},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["operationalStatus"] == "ready"

    def test_status_consistent_between_list_and_detail(self, client, admin_access_token):
        """Verify operationalStatus is same in list and detail responses (AC: #6)."""
        create_resp = _create_peer(
            client, admin_access_token,
            name="consistent-peer",
        )
        peer_id = create_resp.json()["data"]["peerId"]

        # Get from detail endpoint
        detail_resp = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        detail_status = detail_resp.json()["data"]["operationalStatus"]

        # Get from list endpoint
        list_resp = client.get(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
        )
        list_peers = list_resp.json()["data"]
        list_peer = next(p for p in list_peers if p["peerId"] == peer_id)
        list_status = list_peer["operationalStatus"]

        assert detail_status == list_status


class TestPeerOperationalStatusIncomplete:
    """Tests verifying 'incomplete' status via direct DB manipulation (AC: #2, #4).

    Since the API validates inputs at creation time, incomplete peers can only
    occur through direct database manipulation. These tests verify the
    operationalStatus property handles edge cases correctly.
    """

    def test_peer_with_empty_remote_ip_is_incomplete(self, client, admin_access_token):
        """Verify peer with empty remoteIp has 'incomplete' status (AC: #2, #4)."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.services.psk_crypto import encrypt_psk

        gen = get_db_session()
        session = next(gen)
        try:
            peer = Peer(
                name="empty-ip-peer",
                remoteIp="",
                psk=encrypt_psk("test-psk"),
                ikeVersion="ikev2",
            )
            session.add(peer)
            session.commit()
            session.refresh(peer)
            peer_id = peer.peerId
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["operationalStatus"] == "incomplete"

    def test_peer_with_invalid_ip_format_is_incomplete(self, client, admin_access_token):
        """Verify peer with invalid remoteIp format has 'incomplete' status (AC: #4)."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.services.psk_crypto import encrypt_psk

        gen = get_db_session()
        session = next(gen)
        try:
            peer = Peer(
                name="bad-ip-peer",
                remoteIp="not-an-ip-address",
                psk=encrypt_psk("test-psk"),
                ikeVersion="ikev2",
            )
            session.add(peer)
            session.commit()
            session.refresh(peer)
            peer_id = peer.peerId
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["operationalStatus"] == "incomplete"

    def test_peer_with_invalid_ike_version_is_incomplete(self, client, admin_access_token):
        """Verify peer with invalid ikeVersion has 'incomplete' status (AC: #4)."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.services.psk_crypto import encrypt_psk

        gen = get_db_session()
        session = next(gen)
        try:
            peer = Peer(
                name="bad-ike-peer",
                remoteIp="10.1.1.1",
                psk=encrypt_psk("test-psk"),
                ikeVersion="ikev3",
            )
            session.add(peer)
            session.commit()
            session.refresh(peer)
            peer_id = peer.peerId
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        assert response.json()["data"]["operationalStatus"] == "incomplete"

    def test_incomplete_peer_appears_in_list_with_status(self, client, admin_access_token):
        """Verify incomplete peer has correct status in list response (AC: #2, #3)."""
        from backend.app.db.deps import get_db_session
        from backend.app.models.peer import Peer
        from backend.app.services.psk_crypto import encrypt_psk

        # Create one valid peer via API
        _create_peer(client, admin_access_token, name="valid-peer", remote_ip="10.0.0.1")

        # Create one incomplete peer via direct DB
        gen = get_db_session()
        session = next(gen)
        try:
            peer = Peer(
                name="incomplete-list-peer",
                remoteIp="bad-ip",
                psk=encrypt_psk("test-psk"),
                ikeVersion="ikev2",
            )
            session.add(peer)
            session.commit()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        response = client.get(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        peers = response.json()["data"]

        statuses = {p["name"]: p["operationalStatus"] for p in peers}
        assert statuses["valid-peer"] == "ready"
        assert statuses["incomplete-list-peer"] == "incomplete"
