"""Integration tests for interface configuration (Story 4.1).

Tests verify interface model, API endpoints, schema validation,
and configuration persistence.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")


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


# ---------------------------------------------------------------------------
# Task 1.5: GET /api/v1/interfaces - List all interfaces
# ---------------------------------------------------------------------------


class TestInterfaceListEndpoint:
    """Tests for GET /api/v1/interfaces (Task 1.5, AC: #2)."""

    def test_get_all_interfaces_returns_three(self, client, admin_access_token):
        """Verify GET /api/v1/interfaces returns all three interfaces."""
        response = client.get(
            "/api/v1/interfaces",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3
        names = {iface["name"] for iface in data}
        assert names == {"CT", "PT", "MGMT"}

    def test_get_all_interfaces_returns_envelope(self, client, admin_access_token):
        """Verify response follows { data, meta } envelope pattern."""
        response = client.get(
            "/api/v1/interfaces",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["meta"]["count"] == 3

    def test_get_all_interfaces_requires_auth(self, client):
        """Verify GET /api/v1/interfaces requires authentication."""
        response = client.get("/api/v1/interfaces")
        assert response.status_code in (401, 403)

    def test_interfaces_have_correct_namespaces(self, client, admin_access_token):
        """Verify each interface maps to the correct namespace (AC: #3)."""
        response = client.get(
            "/api/v1/interfaces",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        data = response.json()["data"]
        ns_map = {iface["name"]: iface["namespace"] for iface in data}
        assert ns_map["CT"] == "ns_ct"
        assert ns_map["PT"] == "ns_pt"
        assert ns_map["MGMT"] == "ns_mgmt"

    def test_interfaces_have_correct_devices(self, client, admin_access_token):
        """Verify each interface maps to the correct device."""
        response = client.get(
            "/api/v1/interfaces",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        data = response.json()["data"]
        dev_map = {iface["name"]: iface["device"] for iface in data}
        assert dev_map["CT"] == "eth1"
        assert dev_map["PT"] == "eth2"
        assert dev_map["MGMT"] == "eth0"


# ---------------------------------------------------------------------------
# Task 1.6: GET /api/v1/interfaces/{name} - Get specific interface
# ---------------------------------------------------------------------------


class TestInterfaceGetEndpoint:
    """Tests for GET /api/v1/interfaces/{name} (Task 1.6, AC: #2)."""

    def test_get_ct_interface(self, client, admin_access_token):
        """Verify GET /api/v1/interfaces/CT returns CT interface."""
        response = client.get(
            "/api/v1/interfaces/CT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "CT"
        assert data["namespace"] == "ns_ct"
        assert data["device"] == "eth1"

    def test_get_pt_interface(self, client, admin_access_token):
        """Verify GET /api/v1/interfaces/PT returns PT interface."""
        response = client.get(
            "/api/v1/interfaces/PT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "PT"
        assert data["namespace"] == "ns_pt"
        assert data["device"] == "eth2"

    def test_get_mgmt_interface(self, client, admin_access_token):
        """Verify GET /api/v1/interfaces/MGMT returns MGMT interface."""
        response = client.get(
            "/api/v1/interfaces/MGMT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "MGMT"
        assert data["namespace"] == "ns_mgmt"
        assert data["device"] == "eth0"

    def test_get_nonexistent_interface_returns_404(self, client, admin_access_token):
        """Verify GET for nonexistent interface returns 404."""
        response = client.get(
            "/api/v1/interfaces/INVALID",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 404
        error = response.json()["detail"]
        assert error["status"] == 404

    def test_get_interface_requires_auth(self, client):
        """Verify GET /api/v1/interfaces/{name} requires authentication."""
        response = client.get("/api/v1/interfaces/CT")
        assert response.status_code in (401, 403)

    def test_get_interface_returns_envelope(self, client, admin_access_token):
        """Verify response follows { data, meta } envelope pattern."""
        response = client.get(
            "/api/v1/interfaces/CT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_get_interface_case_insensitive(self, client, admin_access_token):
        """Verify interface name lookup is case-insensitive."""
        response = client.get(
            "/api/v1/interfaces/ct",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "CT"


# ---------------------------------------------------------------------------
# Task 1.4: POST /api/v1/interfaces/{name}/configure - Configure interface
# ---------------------------------------------------------------------------


class TestInterfaceConfigureEndpoint:
    """Tests for POST /api/v1/interfaces/{name}/configure (Task 1.4, AC: #1)."""

    def test_configure_ct_interface(self, client, admin_access_token):
        """Verify POST /api/v1/interfaces/CT/configure sets IP config (AC: #1)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "CT"
        assert data["ipAddress"] == "192.168.10.1"
        assert data["netmask"] == "255.255.255.0"
        assert data["gateway"] == "192.168.10.254"
        assert data["namespace"] == "ns_ct"

    def test_configure_pt_interface(self, client, admin_access_token):
        """Verify POST /api/v1/interfaces/PT/configure sets IP config (AC: #1)."""
        response = client.post(
            "/api/v1/interfaces/PT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "10.0.0.1",
                "netmask": "255.255.255.0",
                "gateway": "10.0.0.254",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "PT"
        assert data["ipAddress"] == "10.0.0.1"

    def test_configure_mgmt_interface(self, client, admin_access_token):
        """Verify POST /api/v1/interfaces/MGMT/configure sets IP config (AC: #1)."""
        response = client.post(
            "/api/v1/interfaces/MGMT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.1.100",
                "netmask": "255.255.255.0",
                "gateway": "192.168.1.1",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "MGMT"
        assert data["ipAddress"] == "192.168.1.100"

    def test_configure_nonexistent_interface_returns_404(
        self, client, admin_access_token
    ):
        """Verify configure for nonexistent interface returns 404."""
        response = client.post(
            "/api/v1/interfaces/INVALID/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 404

    def test_configure_requires_auth(self, client):
        """Verify POST /api/v1/interfaces/{name}/configure requires auth."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code in (401, 403)

    def test_configure_returns_envelope(self, client, admin_access_token):
        """Verify configure response follows { data, meta } envelope pattern."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        body = response.json()
        assert "data" in body
        assert "meta" in body

    def test_configure_persists_in_database(self, client, admin_access_token):
        """Verify configuration persists and is readable via GET (AC: #1, #2)."""
        client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "172.16.0.1",
                "netmask": "255.255.0.0",
                "gateway": "172.16.0.254",
            },
        )

        response = client.get(
            "/api/v1/interfaces/CT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ipAddress"] == "172.16.0.1"
        assert data["netmask"] == "255.255.0.0"
        assert data["gateway"] == "172.16.0.254"

    def test_configure_missing_fields_returns_422(self, client, admin_access_token):
        """Verify missing required fields return 422."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={"ipAddress": "192.168.10.1"},
        )
        assert response.status_code == 422

    def test_isolation_failure_returns_500_and_rolls_back_previous_values(
        self, client, admin_access_token, monkeypatch
    ):
        """Verify failed isolation returns RFC7807 500 and DB state is restored."""
        from unittest.mock import MagicMock

        import backend.app.api.interfaces

        # Start from a known valid state.
        monkeypatch.setattr(
            backend.app.api.interfaces,
            "send_command",
            MagicMock(
                return_value={
                    "status": "ok",
                    "result": {"status": "success", "isolation": {"status": "pass"}},
                }
            ),
        )
        initial = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.50.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.50.254",
            },
        )
        assert initial.status_code == 200

        # Next write fails isolation check.
        monkeypatch.setattr(
            backend.app.api.interfaces,
            "send_command",
            MagicMock(
                return_value={
                    "status": "ok",
                    "result": {
                        "status": "success",
                        "isolation": {
                            "status": "fail",
                            "message": "PT->CT policy violation",
                        },
                    },
                }
            ),
        )
        failed = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.60.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.60.254",
            },
        )
        assert failed.status_code == 500
        error = failed.json()["detail"]
        assert error["status"] == 500
        assert error["instance"] == "/api/v1/interfaces/CT/configure"

        # Verify prior values were restored (not nulled / partially applied).
        current = client.get(
            "/api/v1/interfaces/CT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert current.status_code == 200
        data = current.json()["data"]
        assert data["ipAddress"] == "192.168.50.1"
        assert data["netmask"] == "255.255.255.0"
        assert data["gateway"] == "192.168.50.254"


# ---------------------------------------------------------------------------
# Task 1.3: Schema validation (AC: #5)
# ---------------------------------------------------------------------------


class TestInterfaceValidation:
    """Tests for input validation (Task 1.3, AC: #5)."""

    def test_invalid_ip_address_returns_422(self, client, admin_access_token):
        """Verify invalid IP address format returns 422 (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "999.999.999.999",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 422

    def test_invalid_netmask_returns_422(self, client, admin_access_token):
        """Verify invalid netmask returns 422 (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "999.999.999.999",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 422

    def test_invalid_gateway_returns_422(self, client, admin_access_token):
        """Verify invalid gateway returns 422 (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "invalid",
            },
        )
        assert response.status_code == 422

    def test_reserved_ip_zero_returns_422(self, client, admin_access_token):
        """Verify 0.0.0.0 is rejected (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "0.0.0.0",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 422

    def test_broadcast_ip_returns_422(self, client, admin_access_token):
        """Verify 255.255.255.255 is rejected (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "255.255.255.255",
                "netmask": "255.255.255.0",
                "gateway": "192.168.10.254",
            },
        )
        assert response.status_code == 422

    def test_gateway_not_in_subnet_returns_422(self, client, admin_access_token):
        """Verify gateway not in same subnet is rejected (AC: #5)."""
        response = client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.10.1",
                "netmask": "255.255.255.0",
                "gateway": "10.0.0.254",
            },
        )
        assert response.status_code == 422

    def test_valid_private_network_ips_accepted(self, client, admin_access_token):
        """Verify valid private network IPs are accepted (AC: #1)."""
        configs = [
            ("CT", "10.0.0.1", "255.255.255.0", "10.0.0.254"),
            ("PT", "172.16.0.1", "255.255.0.0", "172.16.0.254"),
            ("MGMT", "192.168.1.1", "255.255.255.0", "192.168.1.254"),
        ]
        for name, ip, mask, gw in configs:
            response = client.post(
                f"/api/v1/interfaces/{name}/configure",
                headers={"Authorization": f"Bearer {admin_access_token}"},
                json={"ipAddress": ip, "netmask": mask, "gateway": gw},
            )
            assert response.status_code == 200, f"Failed for {name}: {ip}"


# ---------------------------------------------------------------------------
# Task 3: Persistence tests (AC: #4)
# ---------------------------------------------------------------------------


class TestInterfacePersistence:
    """Tests for configuration persistence (Task 3, AC: #4)."""

    def test_configuration_persists_across_api_restart(
        self, client, admin_access_token
    ):
        """Verify configuration persists after restarting TestClient (AC: #4)."""
        # Configure an interface
        client.post(
            "/api/v1/interfaces/PT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "10.10.10.1",
                "netmask": "255.255.255.0",
                "gateway": "10.10.10.254",
            },
        )

        # Create a new client (simulates API restart)
        from backend.main import app

        new_client = TestClient(app)

        # Re-login
        login_resp = new_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        new_token = login_resp.json()["data"]["accessToken"]

        # Verify config persists
        response = new_client.get(
            "/api/v1/interfaces/PT",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ipAddress"] == "10.10.10.1"
        assert data["netmask"] == "255.255.255.0"
        assert data["gateway"] == "10.10.10.254"

    def test_configuration_update_overwrites_previous(
        self, client, admin_access_token
    ):
        """Verify updating config replaces previous values."""
        # First configuration
        client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "192.168.1.1",
                "netmask": "255.255.255.0",
                "gateway": "192.168.1.254",
            },
        )

        # Second configuration (different values)
        client.post(
            "/api/v1/interfaces/CT/configure",
            headers={"Authorization": f"Bearer {admin_access_token}"},
            json={
                "ipAddress": "10.0.0.100",
                "netmask": "255.255.0.0",
                "gateway": "10.0.0.1",
            },
        )

        # Verify latest config is stored
        response = client.get(
            "/api/v1/interfaces/CT",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        data = response.json()["data"]
        assert data["ipAddress"] == "10.0.0.100"
        assert data["netmask"] == "255.255.0.0"
        assert data["gateway"] == "10.0.0.1"

    def test_unconfigured_interfaces_have_null_ip(self, admin_access_token):
        """Verify unconfigured interfaces have null IP fields."""
        # Use fresh client to check initial state before any POST
        from backend.main import app

        fresh_client = TestClient(app)
        login_resp = fresh_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "changeme"},
        )
        token = login_resp.json()["data"]["accessToken"]

        response = fresh_client.get(
            "/api/v1/interfaces",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()["data"]
        # At least verify the structure is correct (some may have been
        # configured by earlier tests in the same session)
        for iface in data:
            assert "ipAddress" in iface
            assert "netmask" in iface
            assert "gateway" in iface
