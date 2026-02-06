"""Integration tests for route operations on disabled peers (Story 5.3).

Tests verify that route create/update on disabled peers skips daemon updates
and returns appropriate warnings.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


@pytest.fixture(autouse=True)
def _clean_data():
    """Remove all peers and routes before each test for isolation."""
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


class TestRouteDisabledPeer:
    """Tests for route operations on disabled peers."""

    def test_create_route_on_disabled_peer_skips_daemon(self, client, admin_access_token):
        """Test that creating a route for a disabled peer skips daemon update."""
        with patch("backend.app.api.routes.send_command") as mock_send:
            # Create a disabled peer
            peer_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "disabled-peer",
                    "remoteIp": "10.0.0.1",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert peer_response.status_code == 201
            peer_id = peer_response.json()["data"]["peerId"]

            mock_send.reset_mock()

            # Create a route for the disabled peer
            route_response = client.post(
                "/api/v1/routes",
                json={
                    "peerId": peer_id,
                    "destinationCidr": "192.168.1.0/24",
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert route_response.status_code == 201
            data = route_response.json()

            # Verify route was created
            assert data["data"]["peerId"] == peer_id
            assert data["data"]["destinationCidr"] == "192.168.1.0/24"

            # Verify daemon was NOT called (peer is disabled)
            mock_send.assert_not_called()

            # Verify warning message
            assert "warning" in data["meta"]
            assert "disabled" in data["meta"]["warning"].lower()

    def test_update_route_on_disabled_peer_skips_daemon(self, client, admin_access_token):
        """Test that updating a route for a disabled peer skips daemon update."""
        with patch("backend.app.api.routes.send_command") as mock_send:
            # Create a disabled peer
            peer_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "disabled-peer-2",
                    "remoteIp": "10.0.0.2",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert peer_response.status_code == 201
            peer_id = peer_response.json()["data"]["peerId"]

            # Create a route for the disabled peer
            route_response = client.post(
                "/api/v1/routes",
                json={
                    "peerId": peer_id,
                    "destinationCidr": "192.168.1.0/24",
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert route_response.status_code == 201
            route_id = route_response.json()["data"]["routeId"]

            mock_send.reset_mock()

            # Update the route
            update_response = client.put(
                f"/api/v1/routes/{route_id}",
                json={"destinationCidr": "192.168.2.0/24"},
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert update_response.status_code == 200
            data = update_response.json()

            # Verify route was updated
            assert data["data"]["destinationCidr"] == "192.168.2.0/24"

            # Verify daemon was NOT called (peer is disabled)
            mock_send.assert_not_called()

            # Verify warning message
            assert "warning" in data["meta"]
            assert "disabled" in data["meta"]["warning"].lower()

    def test_create_route_on_enabled_peer_calls_daemon(self, client, admin_access_token):
        """Test that creating a route for an enabled peer calls daemon update."""
        with patch("backend.app.api.routes.send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}

            # Create an enabled peer
            peer_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "enabled-peer",
                    "remoteIp": "10.0.0.3",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": True,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert peer_response.status_code == 201
            peer_id = peer_response.json()["data"]["peerId"]

            mock_send.reset_mock()

            # Create a route for the enabled peer
            route_response = client.post(
                "/api/v1/routes",
                json={
                    "peerId": peer_id,
                    "destinationCidr": "192.168.1.0/24",
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert route_response.status_code == 201

            # Verify daemon WAS called (peer is enabled)
            mock_send.assert_called()
            assert mock_send.call_args[0][0] == "update_routes"

    def test_delete_route_on_disabled_peer_skips_daemon(self, client, admin_access_token):
        """Test that deleting a route for a disabled peer skips daemon update."""
        with patch("backend.app.api.routes.send_command") as mock_send:
            peer_response = client.post(
                "/api/v1/peers",
                json={
                    "name": "disabled-peer-delete-route",
                    "remoteIp": "10.0.0.10",
                    "psk": "test-psk",
                    "ikeVersion": "ikev2",
                    "enabled": False,
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert peer_response.status_code == 201
            peer_id = peer_response.json()["data"]["peerId"]

            route_response = client.post(
                "/api/v1/routes",
                json={
                    "peerId": peer_id,
                    "destinationCidr": "192.168.44.0/24",
                },
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
            assert route_response.status_code == 201
            route_id = route_response.json()["data"]["routeId"]

            mock_send.reset_mock()

            delete_response = client.delete(
                f"/api/v1/routes/{route_id}",
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )

            assert delete_response.status_code == 200
            mock_send.assert_not_called()
            meta = delete_response.json()["meta"]
            assert "warning" in meta
            assert "disabled" in meta["warning"].lower()
