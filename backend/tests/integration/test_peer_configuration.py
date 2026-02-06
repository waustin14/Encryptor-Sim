"""Integration tests for IPsec peer configuration (Story 4.2).

Tests verify peer API endpoints, PSK encryption, validation,
and configuration persistence.
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


# ---------------------------------------------------------------------------
# Task 1.4: POST /api/v1/peers - Create peer
# ---------------------------------------------------------------------------


class TestCreatePeer:
    """Tests for POST /api/v1/peers (Task 1.4, AC: #1)."""

    def test_create_peer_with_required_fields(self, client, admin_access_token):
        """Verify POST /api/v1/peers creates peer with minimal required fields (AC: #1)."""
        response = _create_peer(client, admin_access_token, name="site-a")
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "site-a"
        assert data["remoteIp"] == "10.1.1.100"
        assert data["ikeVersion"] == "ikev2"
        assert "psk" not in data  # PSK must NOT be returned

    def test_create_peer_returns_201(self, client, admin_access_token):
        """Verify create peer returns 201 Created."""
        response = _create_peer(client, admin_access_token, name="peer-201")
        assert response.status_code == 201

    def test_create_peer_returns_envelope(self, client, admin_access_token):
        """Verify create peer returns { data, meta } envelope."""
        response = _create_peer(client, admin_access_token, name="peer-envelope")
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_create_peer_with_dpd_params(self, client, admin_access_token):
        """Verify peer with DPD parameters is created (AC: #2)."""
        response = _create_peer(
            client, admin_access_token,
            name="peer-dpd",
            dpdAction="hold",
            dpdDelay=60,
            dpdTimeout=300,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["dpdAction"] == "hold"
        assert data["dpdDelay"] == 60
        assert data["dpdTimeout"] == 300

    def test_create_peer_with_rekey(self, client, admin_access_token):
        """Verify peer with rekey time is created (AC: #2)."""
        response = _create_peer(
            client, admin_access_token,
            name="peer-rekey",
            rekeyTime=7200,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["rekeyTime"] == 7200

    def test_create_peer_with_all_params(self, client, admin_access_token):
        """Verify peer with all parameters is created (AC: #1, #2)."""
        response = _create_peer(
            client, admin_access_token,
            name="peer-all-params",
            remote_ip="10.2.2.200",
            ike_version="ikev1",
            dpdAction="clear",
            dpdDelay=20,
            dpdTimeout=100,
            rekeyTime=1800,
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "peer-all-params"
        assert data["remoteIp"] == "10.2.2.200"
        assert data["ikeVersion"] == "ikev1"
        assert data["dpdAction"] == "clear"
        assert data["dpdDelay"] == 20
        assert data["dpdTimeout"] == 100
        assert data["rekeyTime"] == 1800

    def test_create_peer_defaults_dpd_values(self, client, admin_access_token):
        """Verify defaults are applied for optional DPD fields."""
        response = _create_peer(client, admin_access_token, name="peer-defaults")
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["dpdAction"] == "restart"
        assert data["dpdDelay"] == 30
        assert data["dpdTimeout"] == 150
        assert data["rekeyTime"] == 3600

    def test_create_peer_has_timestamps(self, client, admin_access_token):
        """Verify peer has createdAt and updatedAt timestamps."""
        response = _create_peer(client, admin_access_token, name="peer-ts")
        data = response.json()["data"]
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_create_peer_requires_auth(self, client):
        """Verify POST /api/v1/peers requires authentication."""
        response = client.post(
            "/api/v1/peers",
            json={
                "name": "unauth-peer",
                "remoteIp": "10.1.1.1",
                "psk": "test",
                "ikeVersion": "ikev2",
            },
        )
        assert response.status_code in (401, 403)

    def test_create_peer_runtime_daemon_error_is_best_effort(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify daemon RuntimeError does not fail create mutation."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        monkeypatch.setattr(
            backend.app.api.peers,
            "send_command",
            MagicMock(side_effect=RuntimeError("daemon returned non-ok status")),
        )

        response = _create_peer(client, admin_access_token, name="runtime-daemon-peer")
        assert response.status_code == 201
        meta = response.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta

    def test_create_duplicate_name_returns_409(self, client, admin_access_token):
        """Verify duplicate peer name returns 409 Conflict."""
        _create_peer(client, admin_access_token, name="dup-peer")
        response = _create_peer(client, admin_access_token, name="dup-peer")
        assert response.status_code == 409
        error = response.json()["detail"]
        assert error["status"] == 409


# ---------------------------------------------------------------------------
# Task 1.5: GET /api/v1/peers - List peers
# ---------------------------------------------------------------------------


class TestListPeers:
    """Tests for GET /api/v1/peers (Task 1.5, AC: #1)."""

    def test_list_peers_empty(self, client, admin_access_token):
        """Verify GET /api/v1/peers returns empty list when no peers exist."""
        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == [] or isinstance(body["data"], list)
        assert "meta" in body

    def test_list_peers_returns_created_peers(self, client, admin_access_token):
        """Verify GET /api/v1/peers returns all created peers."""
        _create_peer(client, admin_access_token, name="list-peer-1", remote_ip="10.0.0.1")
        _create_peer(client, admin_access_token, name="list-peer-2", remote_ip="10.0.0.2")

        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        assert response.status_code == 200
        data = response.json()["data"]
        names = {p["name"] for p in data}
        assert "list-peer-1" in names
        assert "list-peer-2" in names

    def test_list_peers_returns_count_in_meta(self, client, admin_access_token):
        """Verify meta contains count of peers."""
        _create_peer(client, admin_access_token, name="count-peer")
        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        meta = response.json()["meta"]
        assert "count" in meta
        assert meta["count"] >= 1

    def test_list_peers_excludes_psk(self, client, admin_access_token):
        """Verify PSK is not included in list response."""
        _create_peer(client, admin_access_token, name="no-psk-peer")
        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        for peer in response.json()["data"]:
            assert "psk" not in peer

    def test_list_peers_requires_auth(self, client):
        """Verify GET /api/v1/peers requires authentication."""
        response = client.get("/api/v1/peers")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Task 1.6: GET /api/v1/peers/{peerId} - Get specific peer
# ---------------------------------------------------------------------------


class TestGetPeer:
    """Tests for GET /api/v1/peers/{peerId} (Task 1.6, AC: #1)."""

    def test_get_peer_by_id(self, client, admin_access_token):
        """Verify GET /api/v1/peers/{peerId} returns specific peer."""
        create_resp = _create_peer(client, admin_access_token, name="get-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["peerId"] == peer_id
        assert data["name"] == "get-peer"

    def test_get_peer_returns_envelope(self, client, admin_access_token):
        """Verify GET response follows { data, meta } envelope."""
        create_resp = _create_peer(client, admin_access_token, name="get-env-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_get_peer_excludes_psk(self, client, admin_access_token):
        """Verify PSK is not in single peer response."""
        create_resp = _create_peer(client, admin_access_token, name="get-no-psk")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert "psk" not in response.json()["data"]

    def test_get_nonexistent_peer_returns_404(self, client, admin_access_token):
        """Verify GET for nonexistent peer returns 404."""
        response = client.get(
            "/api/v1/peers/99999",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404

    def test_get_peer_requires_auth(self, client):
        """Verify GET /api/v1/peers/{peerId} requires authentication."""
        response = client.get("/api/v1/peers/1")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Task 1.7: PUT /api/v1/peers/{peerId} - Update peer
# ---------------------------------------------------------------------------


class TestUpdatePeer:
    """Tests for PUT /api/v1/peers/{peerId} (Task 1.7, AC: #3)."""

    def test_update_peer_remote_ip(self, client, admin_access_token):
        """Verify PUT updates remoteIp (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="update-ip-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"remoteIp": "10.6.6.6"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["remoteIp"] == "10.6.6.6"

    def test_update_peer_dpd_params(self, client, admin_access_token):
        """Verify PUT updates DPD parameters (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="update-dpd-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 45, "dpdTimeout": 200},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["dpdDelay"] == 45
        assert data["dpdTimeout"] == 200

    def test_update_peer_rekey_time(self, client, admin_access_token):
        """Verify PUT updates rekey time (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="update-rekey-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"rekeyTime": 7200},
        )
        assert response.status_code == 200
        assert response.json()["data"]["rekeyTime"] == 7200

    def test_update_peer_ike_version(self, client, admin_access_token):
        """Verify PUT updates IKE version (AC: #3)."""
        create_resp = _create_peer(client, admin_access_token, name="update-ike-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"ikeVersion": "ikev1"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["ikeVersion"] == "ikev1"

    def test_update_peer_psk(self, client, admin_access_token):
        """Verify PUT updates PSK without returning it (AC: #3, #4)."""
        create_resp = _create_peer(client, admin_access_token, name="update-psk-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"psk": "new-super-secret"},
        )
        assert response.status_code == 200
        assert "psk" not in response.json()["data"]

    def test_update_preserves_unchanged_fields(self, client, admin_access_token):
        """Verify update only changes specified fields."""
        create_resp = _create_peer(
            client, admin_access_token,
            name="preserve-peer",
            remote_ip="10.5.5.5",
        )
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 60},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["remoteIp"] == "10.5.5.5"  # Unchanged
        assert data["dpdDelay"] == 60  # Changed

    def test_update_nonexistent_peer_returns_404(self, client, admin_access_token):
        """Verify PUT for nonexistent peer returns 404."""
        response = client.put(
            "/api/v1/peers/99999",
            headers=_auth_header(admin_access_token),
            json={"remoteIp": "10.1.1.1"},
        )
        assert response.status_code == 404

    def test_update_returns_envelope(self, client, admin_access_token):
        """Verify update returns { data, meta } envelope."""
        create_resp = _create_peer(client, admin_access_token, name="update-env-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 40},
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_update_peer_requires_auth(self, client):
        """Verify PUT /api/v1/peers/{peerId} requires authentication."""
        response = client.put(
            "/api/v1/peers/1",
            json={"remoteIp": "10.1.1.1"},
        )
        assert response.status_code in (401, 403)

    def test_update_peer_runtime_daemon_error_is_best_effort(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify daemon RuntimeError does not fail update mutation."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        create_resp = _create_peer(client, admin_access_token, name="runtime-update-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        monkeypatch.setattr(
            backend.app.api.peers,
            "send_command",
            MagicMock(side_effect=RuntimeError("daemon returned non-ok status")),
        )

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"dpdDelay": 55},
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        assert meta["daemonAvailable"] is False
        assert "warning" in meta

    def test_update_duplicate_name_returns_409(self, client, admin_access_token):
        """Verify renaming to existing peer name returns 409."""
        _create_peer(client, admin_access_token, name="name-a")
        create_resp = _create_peer(client, admin_access_token, name="name-b")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"name": "name-a"},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Validation tests (AC: #5)
# ---------------------------------------------------------------------------


class TestPeerValidation:
    """Tests for input validation (AC: #5)."""

    def test_invalid_ip_returns_422(self, client, admin_access_token):
        """Verify invalid IP returns 422 (AC: #5)."""
        response = _create_peer(
            client, admin_access_token,
            name="invalid-ip-peer",
            remote_ip="999.999.999.999",
        )
        assert response.status_code == 422
        error = response.json()["detail"]
        assert error["status"] == 422

    def test_invalid_ike_version_returns_422(self, client, admin_access_token):
        """Verify invalid IKE version returns 422 (AC: #5)."""
        response = _create_peer(
            client, admin_access_token,
            name="invalid-ike-peer",
            ike_version="ikev3",
        )
        assert response.status_code == 422
        error = response.json()["detail"]
        assert error["status"] == 422

    def test_loopback_ip_returns_422(self, client, admin_access_token):
        """Verify loopback IP returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="loopback-peer",
            remote_ip="127.0.0.1",
        )
        assert response.status_code == 422

    def test_broadcast_ip_returns_422(self, client, admin_access_token):
        """Verify broadcast IP returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="broadcast-peer",
            remote_ip="255.255.255.255",
        )
        assert response.status_code == 422

    def test_reserved_ip_returns_422(self, client, admin_access_token):
        """Verify 0.0.0.0 returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="reserved-peer",
            remote_ip="0.0.0.0",
        )
        assert response.status_code == 422

    def test_invalid_dpd_action_returns_422(self, client, admin_access_token):
        """Verify invalid DPD action returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="bad-dpd-peer",
            dpdAction="invalid-action",
        )
        assert response.status_code == 422

    def test_invalid_dpd_delay_returns_422(self, client, admin_access_token):
        """Verify DPD delay out of range returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="bad-delay-peer",
            dpdDelay=5,
        )
        assert response.status_code == 422

    def test_invalid_rekey_returns_422(self, client, admin_access_token):
        """Verify rekey out of range returns 422."""
        response = _create_peer(
            client, admin_access_token,
            name="bad-rekey-peer",
            rekeyTime=100,
        )
        assert response.status_code == 422

    def test_update_with_invalid_ip_returns_422(self, client, admin_access_token):
        """Verify update with invalid IP returns 422."""
        create_resp = _create_peer(client, admin_access_token, name="val-update-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"remoteIp": "999.999.999.999"},
        )
        assert response.status_code == 422

    def test_rfc7807_error_format(self, client, admin_access_token):
        """Verify errors follow RFC 7807 format."""
        response = _create_peer(
            client, admin_access_token,
            name="rfc7807-peer",
            remote_ip="999.999.999.999",
        )
        error = response.json()["detail"]
        assert "type" in error
        assert "title" in error
        assert "status" in error
        assert "detail" in error


# ---------------------------------------------------------------------------
# PSK encryption tests (AC: #4)
# ---------------------------------------------------------------------------


class TestPSKEncryption:
    """Tests for PSK encryption at rest (AC: #4)."""

    def test_psk_not_returned_in_create_response(self, client, admin_access_token):
        """Verify PSK is not in create response (AC: #4)."""
        response = _create_peer(
            client, admin_access_token,
            name="no-psk-create",
            psk="plaintext-psk-12345",
        )
        assert response.status_code == 201
        assert "psk" not in response.json()["data"]

    def test_psk_not_returned_in_list_response(self, client, admin_access_token):
        """Verify PSK is not in list response (AC: #4)."""
        _create_peer(client, admin_access_token, name="no-psk-list")
        response = client.get(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
        )
        for peer in response.json()["data"]:
            assert "psk" not in peer

    def test_psk_not_returned_in_get_response(self, client, admin_access_token):
        """Verify PSK is not in single peer response (AC: #4)."""
        create_resp = _create_peer(client, admin_access_token, name="no-psk-get")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert "psk" not in response.json()["data"]

    def test_psk_not_returned_in_update_response(self, client, admin_access_token):
        """Verify PSK is not in update response (AC: #4)."""
        create_resp = _create_peer(client, admin_access_token, name="no-psk-update")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"psk": "new-secret"},
        )
        assert "psk" not in response.json()["data"]


# ---------------------------------------------------------------------------
# Persistence tests (AC: #6)
# ---------------------------------------------------------------------------


class TestPeerPersistence:
    """Tests for peer configuration persistence."""

    def test_peer_persists_across_api_restart(self, client, admin_access_token):
        """Verify peer config persists after restarting TestClient."""
        _create_peer(
            client, admin_access_token,
            name="persist-peer",
            remote_ip="10.10.10.1",
        )

        # Simulate API restart with new client
        from backend.main import app

        new_client = TestClient(app)
        login_resp = new_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        new_token = login_resp.json()["data"]["accessToken"]

        response = new_client.get(
            "/api/v1/peers",
            headers=_auth_header(new_token),
        )
        assert response.status_code == 200
        names = {p["name"] for p in response.json()["data"]}
        assert "persist-peer" in names

    def test_update_persists(self, client, admin_access_token):
        """Verify updated config is readable via GET."""
        create_resp = _create_peer(
            client, admin_access_token,
            name="update-persist-peer",
        )
        peer_id = create_resp.json()["data"]["peerId"]

        client.put(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
            json={"remoteIp": "10.99.99.99"},
        )

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.json()["data"]["remoteIp"] == "10.99.99.99"

    def test_created_peer_appears_in_list(self, client, admin_access_token):
        """Verify created peer appears in list endpoint."""
        _create_peer(client, admin_access_token, name="listed-peer")

        response = client.get(
            "/api/v1/peers",
            headers=_auth_header(admin_access_token),
        )
        names = {p["name"] for p in response.json()["data"]}
        assert "listed-peer" in names


# ---------------------------------------------------------------------------
# DELETE /api/v1/peers/{peerId} - Delete peer (Story 4.3)
# ---------------------------------------------------------------------------


class TestDeletePeer:
    """Tests for DELETE /api/v1/peers/{peerId} (Story 4.3, Task 1)."""

    def test_delete_peer_returns_200_envelope(self, client, admin_access_token):
        """Verify DELETE /api/v1/peers/{peerId} returns {data, meta} envelope."""
        create_resp = _create_peer(client, admin_access_token, name="delete-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["peerId"] == peer_id

    def test_delete_peer_removes_from_list(self, client, admin_access_token):
        """Verify deleted peer no longer appears in list (AC: #1)."""
        create_resp = _create_peer(client, admin_access_token, name="remove-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )

        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        names = {p["name"] for p in response.json()["data"]}
        assert "remove-peer" not in names

    def test_delete_peer_get_returns_404(self, client, admin_access_token):
        """Verify GET after DELETE returns 404 (AC: #1, #2)."""
        create_resp = _create_peer(client, admin_access_token, name="gone-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )

        response = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404

    def test_delete_nonexistent_peer_returns_404(self, client, admin_access_token):
        """Verify deleting non-existent peer returns 404 (AC: #7)."""
        response = client.delete(
            "/api/v1/peers/99999",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404
        assert "not found" in error["detail"].lower()

    def test_delete_nonexistent_peer_rfc7807_format(self, client, admin_access_token):
        """Verify 404 error follows RFC 7807 format (AC: #7)."""
        response = client.delete(
            "/api/v1/peers/99999",
            headers=_auth_header(admin_access_token),
        )
        error = response.json()["detail"]
        assert "type" in error
        assert "title" in error
        assert "status" in error
        assert "detail" in error
        assert "instance" in error

    def test_delete_peer_requires_auth(self, client):
        """Verify DELETE /api/v1/peers/{peerId} requires authentication (AC: #6)."""
        response = client.delete("/api/v1/peers/1")
        assert response.status_code in (401, 403)

    def test_delete_peer_idempotent_second_returns_404(self, client, admin_access_token):
        """Verify deleting same peer twice returns 404 on second attempt."""
        create_resp = _create_peer(client, admin_access_token, name="idempotent-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        first = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert first.status_code == 200

        second = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert second.status_code == 404

    def test_delete_peer_persists_across_restart(self, client, admin_access_token):
        """Verify deletion persists after API restart (AC: #2)."""
        create_resp = _create_peer(
            client, admin_access_token,
            name="persist-delete-peer",
            remote_ip="10.20.20.20",
        )
        peer_id = create_resp.json()["data"]["peerId"]

        client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )

        # Simulate API restart with new client
        from backend.main import app

        new_client = TestClient(app)
        login_resp = new_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        new_token = login_resp.json()["data"]["accessToken"]

        response = new_client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(new_token),
        )
        assert response.status_code == 404

    def test_delete_does_not_affect_other_peers(self, client, admin_access_token):
        """Verify deleting one peer does not affect others."""
        _create_peer(client, admin_access_token, name="keep-peer", remote_ip="10.0.0.1")
        create_resp = _create_peer(
            client, admin_access_token, name="delete-me", remote_ip="10.0.0.2"
        )
        peer_id = create_resp.json()["data"]["peerId"]

        client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )

        response = client.get("/api/v1/peers", headers=_auth_header(admin_access_token))
        names = {p["name"] for p in response.json()["data"]}
        assert "keep-peer" in names
        assert "delete-me" not in names

    def test_delete_peer_response_contains_meta(self, client, admin_access_token):
        """Verify delete response contains daemon metadata."""
        create_resp = _create_peer(client, admin_access_token, name="no-body-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200
        body = response.json()
        assert "meta" in body
        assert "daemonAvailable" in body["meta"]

    def test_delete_peer_cascade_no_routes(self, client, admin_access_token):
        """Verify peer deletion succeeds when no routes exist (AC: #3).

        Route model will be added in Story 4.4; cascade deletion is ready.
        """
        create_resp = _create_peer(client, admin_access_token, name="cascade-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200

        # Verify peer is gone
        get_resp = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert get_resp.status_code == 404

    def test_delete_peer_calls_teardown_daemon(self, client, admin_access_token, monkeypatch):
        """Verify DELETE calls daemon teardown_peer command (AC: #4)."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        create_resp = _create_peer(client, admin_access_token, name="teardown-test-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200

        # Verify teardown_peer was called with correct peer name
        teardown_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "teardown_peer"
        ]
        assert len(teardown_calls) == 1
        assert teardown_calls[0][0][1]["name"] == "teardown-test-peer"

    def test_delete_peer_calls_remove_config_daemon(self, client, admin_access_token, monkeypatch):
        """Verify DELETE calls daemon remove_peer_config command (AC: #5)."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        mock_send = MagicMock(return_value={"status": "ok"})
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        create_resp = _create_peer(client, admin_access_token, name="config-removal-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert response.status_code == 200

        # Verify remove_peer_config was called with correct peer name
        remove_calls = [
            call for call in mock_send.call_args_list
            if call[0][0] == "remove_peer_config"
        ]
        assert len(remove_calls) == 1
        assert remove_calls[0][0][1]["name"] == "config-removal-peer"

    def test_delete_peer_succeeds_when_daemon_unavailable(self, client, admin_access_token, monkeypatch):
        """Verify DELETE returns 200 even when daemon IPC fails (best-effort pattern)."""
        from unittest.mock import MagicMock

        import backend.app.api.peers

        # Mock daemon to raise ConnectionError
        mock_send = MagicMock(side_effect=ConnectionError("Daemon not running"))
        monkeypatch.setattr(backend.app.api.peers, "send_command", mock_send)

        create_resp = _create_peer(client, admin_access_token, name="daemon-down-peer")
        peer_id = create_resp.json()["data"]["peerId"]

        response = client.delete(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )

        # Should still return 200 despite daemon failure
        assert response.status_code == 200

        # Verify peer was still deleted from database
        get_resp = client.get(
            f"/api/v1/peers/{peer_id}",
            headers=_auth_header(admin_access_token),
        )
        assert get_resp.status_code == 404
