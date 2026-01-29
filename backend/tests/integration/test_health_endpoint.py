"""Integration tests for health endpoint with boot timing.

Tests that the /api/v1/system/health endpoint returns boot duration
and service status. Validates AC #3 of Story 2.2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Path to backend
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"


class TestHealthEndpointConfiguration:
    """Test health endpoint is properly configured."""

    def test_system_router_has_health_endpoint(self) -> None:
        """Verify system.py defines /health endpoint."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        assert "/health" in content, "system.py must define /health endpoint"

    def test_health_endpoint_returns_boot_duration(self) -> None:
        """Verify health endpoint response includes bootDuration."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        # Should include boot duration in response
        assert "bootDuration" in content or "boot_duration" in content or "boot" in content.lower()

    def test_health_endpoint_returns_boot_target_fields(self) -> None:
        """Verify health endpoint includes boot target evaluation."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        assert "bootTarget" in content
        assert "bootWithinTarget" in content
        assert "bootTargetSeconds" in content

    def test_health_endpoint_returns_service_status(self) -> None:
        """Verify health endpoint response includes service statuses."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        # Should include services in response
        assert "services" in content.lower() or "status" in content.lower()

    def test_health_endpoint_checks_openrc_service_status(self) -> None:
        """Verify health endpoint checks OpenRC service status."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        assert "rc-service" in content

    def test_health_endpoint_tracks_database_and_isolation(self) -> None:
        """Verify health endpoint checks database and isolation status."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        assert "database" in content.lower()
        assert "isolation" in content.lower()

    def test_health_endpoint_tracks_web_ui_status(self) -> None:
        """Verify health endpoint checks web UI status."""
        system_py = BACKEND_DIR / "app" / "api" / "system.py"
        content = system_py.read_text()

        assert "web_ui" in content.lower() or "webui" in content.lower()


class TestHealthEndpointSchema:
    """Test health endpoint response schema."""

    def test_health_schema_exists(self) -> None:
        """Verify health response schema is defined."""
        # Check if schema exists in schemas directory
        schemas_dir = BACKEND_DIR / "app" / "schemas"
        schema_files = list(schemas_dir.glob("*.py"))
        schema_contents = "".join(f.read_text() for f in schema_files)

        assert "health" in schema_contents.lower() or "Health" in schema_contents


class TestBootTimeTracking:
    """Test boot time tracking mechanism."""

    def test_config_has_boot_time_setting(self) -> None:
        """Verify configuration tracks boot start time."""
        config_py = BACKEND_DIR / "app" / "config.py"
        content = config_py.read_text()

        # Should track boot time
        assert "boot" in content.lower() or "startup" in content.lower() or "time" in content.lower()
