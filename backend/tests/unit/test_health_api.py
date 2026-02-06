"""Unit tests for the health endpoint."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.main import app


client = TestClient(app)

def _auth_headers() -> dict[str, str]:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_returns_200() -> None:
    """Verify health endpoint returns 200 OK."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())

    assert response.status_code == 200


def test_health_endpoint_returns_correct_structure() -> None:
    """Verify health endpoint returns { data, meta } envelope."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    body = response.json()

    assert "data" in body
    assert "meta" in body


def test_health_endpoint_data_contains_required_fields() -> None:
    """Verify health data contains status, bootDuration, services, timestamp."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    data = response.json()["data"]

    assert "status" in data
    assert "bootDuration" in data
    assert "bootTarget" in data
    assert "bootTargetSeconds" in data
    assert "bootWithinTarget" in data
    assert "services" in data
    assert "timestamp" in data


def test_health_endpoint_services_contains_all_components() -> None:
    """Verify services object contains namespaces, daemon, api."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    services = response.json()["data"]["services"]

    assert "namespaces" in services
    assert "daemon" in services
    assert "api" in services
    assert "database" in services
    assert "isolation" in services
    assert "webUi" in services


def test_health_endpoint_boot_duration_is_positive() -> None:
    """Verify bootDuration is a positive number or null (Story 2.5: can be None if timestamps missing)."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    data = response.json()["data"]
    boot_duration = data["bootDuration"]
    boot_target = data["bootTarget"]
    boot_target_seconds = data["bootTargetSeconds"]
    boot_within_target = data["bootWithinTarget"]

    # bootDuration can be None if boot timestamps are not available
    # (e.g., running in development without boot timestamp files)
    if boot_duration is not None:
        assert isinstance(boot_duration, (int, float))
        assert boot_duration >= 0
        assert boot_target == (boot_duration < boot_target_seconds)
        assert boot_within_target == boot_target
    else:
        assert boot_target is None, "bootTarget should be None when bootDuration is None"
        assert boot_within_target is None, "bootWithinTarget should be None when bootDuration is None"

    assert isinstance(boot_target_seconds, (int, float))
    assert boot_target_seconds > 0


def test_health_endpoint_api_status_is_running() -> None:
    """Verify API status is 'running' when endpoint responds."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    api_status = response.json()["data"]["services"]["api"]

    assert api_status == "running"


def test_health_endpoint_includes_mgmt_interface() -> None:
    """Verify health endpoint includes mgmtInterface field (AC: #1, #2)."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    data = response.json()["data"]

    assert "mgmtInterface" in data, "Health response must include mgmtInterface"


def test_health_endpoint_mgmt_interface_has_required_fields() -> None:
    """Verify mgmtInterface contains interface, ip, method, status fields."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    assert "interface" in mgmt, "Must include interface name"
    assert "ip" in mgmt, "Must include IP address (may be null)"
    assert "method" in mgmt, "Must include configuration method (dhcp/static/unknown)"
    assert "leaseStatus" in mgmt, "Must include DHCP lease status (obtained/failed/static/unknown)"
    assert "status" in mgmt, "Must include interface status (up/down/unknown)"


def test_health_endpoint_mgmt_interface_method_values() -> None:
    """Verify method field has valid value."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    valid_methods = {"dhcp", "static", "unknown"}
    assert mgmt["method"] in valid_methods, f"Method must be one of {valid_methods}"


def test_health_endpoint_mgmt_interface_status_values() -> None:
    """Verify status field has valid value."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    valid_statuses = {"up", "down", "unknown", "error"}
    assert mgmt["status"] in valid_statuses, f"Status must be one of {valid_statuses}"


def test_health_endpoint_mgmt_interface_lease_status_values() -> None:
    """Verify leaseStatus field has valid value."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    valid_lease_statuses = {"obtained", "failed", "static", "unknown"}
    assert mgmt["leaseStatus"] in valid_lease_statuses, (
        f"leaseStatus must be one of {valid_lease_statuses}"
    )


def test_health_endpoint_mgmt_interface_includes_netmask() -> None:
    """Verify mgmtInterface includes netmask field (Story 2.4)."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    assert "netmask" in mgmt, "Must include netmask field"
    # netmask can be null or a valid IP format
    if mgmt["netmask"] is not None:
        assert isinstance(mgmt["netmask"], str), "netmask must be string or null"


def test_health_endpoint_mgmt_interface_includes_gateway() -> None:
    """Verify mgmtInterface includes gateway field (Story 2.4)."""
    response = client.get("/api/v1/system/health", headers=_auth_headers())
    mgmt = response.json()["data"]["mgmtInterface"]

    assert "gateway" in mgmt, "Must include gateway field"
    # gateway can be null or a valid IP format
    if mgmt["gateway"] is not None:
        assert isinstance(mgmt["gateway"], str), "gateway must be string or null"


# Story 2.5: Boot metrics tests

class TestBootDurationFromTimestamps:
    """Test boot duration calculation from timestamp files (Story 2.5)."""

    def test_calculate_boot_duration_from_timestamp_files(self, tmp_path, monkeypatch) -> None:
        """Verify boot duration is calculated from boot-start and boot-complete files (AC: #1)."""
        from backend.app import config

        # Create mock timestamp files
        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        (boot_dir / "boot-start").write_text("1000.0\n")
        (boot_dir / "boot-complete").write_text("1025.5\n")

        # Monkeypatch the timestamp directory
        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        assert duration == 25.5, "Boot duration should be 25.5 seconds (1025.5 - 1000.0)"

    def test_boot_duration_returns_none_when_start_missing(self, tmp_path, monkeypatch) -> None:
        """Verify boot duration returns None when boot-start is missing (Task 3.5)."""
        from backend.app import config

        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        # Only boot-complete exists
        (boot_dir / "boot-complete").write_text("1025.5\n")

        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        assert duration is None, "Duration should be None when boot-start is missing"

    def test_boot_duration_returns_none_when_complete_missing(self, tmp_path, monkeypatch) -> None:
        """Verify boot duration returns None when boot-complete is missing (Task 3.5)."""
        from backend.app import config

        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        # Only boot-start exists
        (boot_dir / "boot-start").write_text("1000.0\n")

        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        assert duration is None, "Duration should be None when boot-complete is missing"

    def test_boot_duration_returns_none_when_directory_missing(self, tmp_path, monkeypatch) -> None:
        """Verify boot duration returns None when timestamp directory doesn't exist."""
        from backend.app import config

        # Point to non-existent directory
        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(tmp_path / "nonexistent"))

        duration = config.get_boot_duration_seconds()
        assert duration is None, "Duration should be None when directory doesn't exist"

    def test_boot_duration_rounded_to_one_decimal(self, tmp_path, monkeypatch) -> None:
        """Verify boot duration is rounded to one decimal place (Story 2.5)."""
        from backend.app import config

        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        (boot_dir / "boot-start").write_text("1000.123456\n")
        (boot_dir / "boot-complete").write_text("1023.789012\n")

        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        # 1023.789012 - 1000.123456 = 23.665556 → rounded to 23.7
        assert duration == 23.7, "Duration should be rounded to one decimal place"

    def test_boot_target_true_when_under_30s(self, tmp_path, monkeypatch) -> None:
        """Verify bootWithinTarget is True when duration < 30s (AC: #2)."""
        from backend.app import config

        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        (boot_dir / "boot-start").write_text("1000.0\n")
        (boot_dir / "boot-complete").write_text("1023.5\n")  # 23.5 seconds

        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        assert duration == 23.5
        assert duration < config.BOOT_TARGET_SECONDS

    def test_boot_target_false_when_over_30s(self, tmp_path, monkeypatch) -> None:
        """Verify bootWithinTarget is False when duration >= 30s (AC: #2)."""
        from backend.app import config

        boot_dir = tmp_path / "encryptor"
        boot_dir.mkdir()
        (boot_dir / "boot-start").write_text("1000.0\n")
        (boot_dir / "boot-complete").write_text("1035.0\n")  # 35 seconds

        monkeypatch.setattr(config, "BOOT_TIMESTAMP_DIR", str(boot_dir))

        duration = config.get_boot_duration_seconds()
        assert duration == 35.0
        assert duration > config.BOOT_TARGET_SECONDS
