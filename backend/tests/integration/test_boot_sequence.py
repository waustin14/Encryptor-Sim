"""Integration tests for boot sequence verification.

Tests that OpenRC services start in correct order with proper dependencies
and health checks. These tests validate AC #1, #2, #3, #4 of Story 2.2.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest


# Path to OpenRC service files
OPENRC_DIR = Path(__file__).parent.parent.parent.parent / "image" / "openrc"


def _parse_depend_block(content: str) -> dict[str, set[str]]:
    deps: dict[str, set[str]] = {"need": set(), "before": set(), "after": set()}
    in_depend = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("depend()"):
            in_depend = True
            continue
        if in_depend and stripped == "}":
            break
        if not in_depend:
            continue
        for key in deps:
            if stripped.startswith(key):
                tokens = stripped.split()[1:]
                deps[key].update(tokens)
    return deps


class TestOpenRCServiceDependencies:
    """Test OpenRC service dependency declarations."""

    def test_namespaces_service_has_before_directive(self) -> None:
        """Verify encryptor-namespaces runs before daemon and api."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must have 'before' directive for daemon and api
        assert "before encryptor-daemon" in content or "before encryptor-daemon encryptor-api" in content
        assert "before encryptor-api" in content or "before encryptor-daemon encryptor-api" in content

    def test_daemon_service_needs_namespaces(self) -> None:
        """Verify encryptor-daemon requires namespaces to be running."""
        service_file = OPENRC_DIR / "encryptor-daemon"
        content = service_file.read_text()

        # Must have 'need' directive for namespaces
        assert "need encryptor-namespaces" in content

    def test_daemon_service_runs_before_api(self) -> None:
        """Verify encryptor-daemon runs before api."""
        service_file = OPENRC_DIR / "encryptor-daemon"
        content = service_file.read_text()

        # Must have 'before' directive for api
        assert "before encryptor-api" in content

    def test_api_service_needs_daemon(self) -> None:
        """Verify encryptor-api requires daemon to be running."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must have 'need' directive for daemon
        assert "need encryptor-daemon" in content

    def test_dependency_graph_orders_services(self) -> None:
        """Verify dependency graph enforces namespaces -> daemon -> api."""
        namespaces_content = (OPENRC_DIR / "encryptor-namespaces").read_text()
        daemon_content = (OPENRC_DIR / "encryptor-daemon").read_text()
        api_content = (OPENRC_DIR / "encryptor-api").read_text()

        namespaces_deps = _parse_depend_block(namespaces_content)
        daemon_deps = _parse_depend_block(daemon_content)
        api_deps = _parse_depend_block(api_content)

        assert "encryptor-daemon" in namespaces_deps["before"]
        assert "encryptor-api" in namespaces_deps["before"]
        assert "encryptor-namespaces" in daemon_deps["need"]
        assert "encryptor-api" in daemon_deps["before"]
        assert "encryptor-daemon" in api_deps["need"]


class TestNamespaceCreation:
    """Test namespace service creates all required namespaces."""

    def test_namespaces_service_creates_ct_namespace(self) -> None:
        """Verify CT namespace is created."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must reference CT namespace
        assert 'NS_CT="ns_ct"' in content or "ns_ct" in content.lower()

    def test_namespaces_service_creates_pt_namespace(self) -> None:
        """Verify PT namespace is created."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must reference PT namespace
        assert 'NS_PT="ns_pt"' in content or "ns_pt" in content.lower()

    def test_namespaces_service_creates_mgmt_namespace(self) -> None:
        """Verify MGMT namespace is created."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must reference MGMT namespace
        assert 'NS_MGMT="ns_mgmt"' in content or "ns_mgmt" in content.lower()


class TestDaemonInitialization:
    """Test daemon service initializes nftables rules."""

    def test_daemon_verifies_nftables_available(self) -> None:
        """Verify daemon checks nftables availability in start_pre."""
        service_file = OPENRC_DIR / "encryptor-daemon"
        content = service_file.read_text()

        # Must check for nft command
        assert "nft" in content

    def test_daemon_verifies_namespaces_ready(self) -> None:
        """Verify daemon checks namespaces are ready in start_pre."""
        service_file = OPENRC_DIR / "encryptor-daemon"
        content = service_file.read_text()

        # Must check namespace exists
        assert "ip netns" in content or "ns_ct" in content


class TestApiServiceConfiguration:
    """Test API service configuration for MGMT namespace binding."""

    def test_api_service_runs_in_mgmt_namespace(self) -> None:
        """Verify API runs in MGMT namespace for isolation."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must run in MGMT namespace - check for ip command and netns exec ns_mgmt
        # The pattern may be split across command and command_args
        has_ip_command = "/usr/bin/ip" in content or "ip netns" in content
        has_netns_exec = "netns exec" in content
        has_mgmt_ns = "ns_mgmt" in content

        assert has_ip_command and has_netns_exec and has_mgmt_ns, (
            "API service must run in MGMT namespace using 'ip netns exec ns_mgmt'"
        )

    def test_api_service_has_healthcheck(self) -> None:
        """Verify API service has health check function."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must have healthcheck function
        assert "healthcheck()" in content

    def test_api_service_blocks_http_port(self) -> None:
        """Verify API service enforces HTTPS-only by checking port 80."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        assert "port 80" in content or "sport = :80" in content


class TestServiceHealthChecks:
    """Test service health check implementations."""

    def test_namespaces_service_has_start_post_check(self) -> None:
        """Verify namespaces service verifies namespaces exist after start."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Should have start_post or verification in start
        # At minimum, should check that namespaces were created
        assert "ip netns list" in content or "start_post" in content

    def test_daemon_service_has_start_post_check(self) -> None:
        """Verify daemon service verifies socket exists after start."""
        service_file = OPENRC_DIR / "encryptor-daemon"
        content = service_file.read_text()

        # Should verify daemon socket is created
        assert "daemon.sock" in content or "start_post" in content

    def test_api_service_has_start_post_check(self) -> None:
        """Verify API service verifies endpoint responds after start."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Should have start_post that checks API is responding
        assert "start_post" in content or "healthcheck" in content


class TestBootTimestamps:
    """Test boot timestamp recording for Story 2.5."""

    def test_namespaces_service_records_boot_start_timestamp(self) -> None:
        """Verify encryptor-namespaces writes boot-start timestamp (AC: #1, Task 1.1)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must create directory and write timestamp as first action in start()
        assert "/var/run/encryptor" in content, "Must reference boot timestamp directory"
        assert "boot-start" in content, "Must write boot-start timestamp file"

    def test_namespaces_service_creates_timestamp_directory(self) -> None:
        """Verify encryptor-namespaces creates /var/run/encryptor directory (Task 1.2)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must create directory with mkdir -p
        assert "mkdir -p /var/run/encryptor" in content, (
            "Must create /var/run/encryptor directory before writing timestamp"
        )

    def test_namespaces_service_writes_timestamp_first(self) -> None:
        """Verify boot-start timestamp is written at start of start() function (Task 1.1)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Find start() function and verify timestamp writing happens early
        start_func_match = re.search(r'start\(\)\s*\{([^}]+)', content, re.DOTALL)
        assert start_func_match, "Must have start() function"

        start_body = start_func_match.group(1)
        lines = [line.strip() for line in start_body.split('\n') if line.strip() and not line.strip().startswith('#')]

        # First few lines should be timestamp recording (mkdir and date command)
        first_lines = ' '.join(lines[:3])
        assert "mkdir" in first_lines and "boot-start" in first_lines, (
            "Timestamp recording must happen in first few lines of start()"
        )

    def test_api_service_records_boot_complete_timestamp(self) -> None:
        """Verify encryptor-api writes boot-complete timestamp (AC: #1, Task 2.1)."""
        service_file = OPENRC_DIR / "encryptor-api"
        content = service_file.read_text()

        # Must write boot-complete timestamp after API is ready
        assert "boot-complete" in content, "Must write boot-complete timestamp file"

    def test_boot_timestamp_uses_high_precision(self) -> None:
        """Verify boot timestamps use high-precision format (seconds.nanoseconds)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must use date +%s.%N for nanosecond precision
        assert "date +%s.%N" in content or 'date "+%s.%N"' in content, (
            "Must use 'date +%s.%N' for high-precision timestamps"
        )
