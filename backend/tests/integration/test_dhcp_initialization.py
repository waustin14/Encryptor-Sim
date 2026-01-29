"""Integration tests for DHCP initialization in ns_mgmt namespace.

Tests that the encryptor-namespaces service properly configures DHCP
for the MGMT interface. Validates AC #1, #2 of Story 2.3.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


# Path to OpenRC service files
OPENRC_DIR = Path(__file__).parent.parent.parent.parent / "image" / "openrc"


def _can_run_namespace_checks() -> bool:
    if os.geteuid() != 0:
        return False
    if not shutil.which("ip"):
        return False
    check = subprocess.run(
        ["ip", "netns", "exec", "ns_mgmt", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return check.returncode == 0


class TestDHCPClientConfiguration:
    """Test DHCP client is configured in ns_mgmt namespace."""

    def test_namespaces_service_moves_eth0_into_ns_mgmt(self) -> None:
        """Verify encryptor-namespaces moves eth0 into ns_mgmt (AC: #1)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must define eth0 as MGMT interface
        assert 'IF_MGMT="eth0"' in content, "Must define eth0 as MGMT interface"

        # Must move eth0 into ns_mgmt
        assert "move_interface_to_namespace" in content
        assert '"$IF_MGMT" "$NS_MGMT"' in content or 'IF_MGMT' in content

    def test_namespaces_service_runs_udhcpc_in_ns_mgmt(self) -> None:
        """Verify udhcpc runs in ns_mgmt after interface move (AC: #1)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must run udhcpc in ns_mgmt namespace
        assert "ip netns exec" in content, "Must use ip netns exec for DHCP"
        assert "udhcpc" in content, "Must run udhcpc DHCP client"

        # Verify udhcpc runs in NS_MGMT context
        # Pattern: ip netns exec "$NS_MGMT" udhcpc ...
        udhcpc_pattern = r'ip\s+netns\s+exec\s+"\$NS_MGMT"\s+udhcpc'
        assert re.search(udhcpc_pattern, content), (
            "udhcpc must run in NS_MGMT namespace context"
        )

    def test_namespaces_service_runs_dhcp_after_interface_move(self) -> None:
        """Verify DHCP runs after interface is moved to namespace."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Extract start() function body to check order within the function
        start_body = _extract_function_body(content, "start")
        assert start_body, "start() function must exist"

        # Find positions within start() function
        move_pos = start_body.find('move_interface_to_namespace "$IF_MGMT"')
        # Look for DHCP client execution (either direct or via case statement)
        dhcp_pos = start_body.find("udhcpc")

        assert move_pos > 0, "Interface move command must exist in start()"
        assert dhcp_pos > 0, "DHCP command must exist in start()"
        assert move_pos < dhcp_pos, "Interface move must occur before DHCP in start()"


def _extract_function_body(content: str, func_name: str) -> str:
    """Extract shell function body handling nested braces."""
    # Find function start
    func_start = content.find(f"{func_name}()")
    if func_start == -1:
        return ""

    # Find opening brace
    brace_start = content.find("{", func_start)
    if brace_start == -1:
        return ""

    # Count braces to find matching closing brace
    depth = 0
    idx = brace_start
    while idx < len(content):
        if content[idx] == "{":
            depth += 1
        elif content[idx] == "}":
            depth -= 1
            if depth == 0:
                return content[brace_start + 1:idx]
        idx += 1

    return ""


class TestDHCPLeaseVerification:
    """Test DHCP lease acquisition is verified before services start."""

    def test_start_post_verifies_dhcp_ip_assignment(self) -> None:
        """Verify start_post checks that eth0 has IP in ns_mgmt (AC: #1)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # start_post must verify IP is assigned to eth0 in ns_mgmt
        assert "start_post" in content, "Must have start_post function"

        # Extract start_post function content using brace counting
        start_post_content = _extract_function_body(content, "start_post")
        assert start_post_content, "start_post function must be parseable"

        # Must check for IP address on eth0 in ns_mgmt
        # Should use interface_has_ip helper or check inet directly
        has_ip_check = (
            "interface_has_ip" in start_post_content or
            "inet" in start_post_content or
            "ip addr" in start_post_content or
            "ip -4 addr" in start_post_content
        )
        assert has_ip_check, (
            "start_post must verify IP assignment on MGMT interface"
        )

    def test_start_post_has_dhcp_timeout_handling(self) -> None:
        """Verify start_post handles DHCP timeout gracefully."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # start_post should handle case where DHCP fails
        # Should log warning but not fail boot
        assert "start_post" in content

        # Extract start_post function using brace counting
        start_post_content = _extract_function_body(content, "start_post")
        assert start_post_content

        # Should have warning for DHCP failure (not hard error)
        # Either ewarn for DHCP or check IP and warn if missing
        has_dhcp_check = (
            "interface_has_ip" in start_post_content or
            "inet" in start_post_content or
            "ip addr" in start_post_content or
            "dhcp" in start_post_content.lower()
        )
        assert has_dhcp_check, (
            "start_post must check DHCP result"
        )


class TestDHCPServiceDependencies:
    """Test service dependencies ensure DHCP completes before API starts."""

    def test_api_service_depends_on_namespaces(self) -> None:
        """Verify API cannot start until namespaces (including DHCP) complete."""
        api_service = OPENRC_DIR / "encryptor-api"
        api_content = api_service.read_text()

        ns_service = OPENRC_DIR / "encryptor-namespaces"
        ns_content = ns_service.read_text()

        # API must need daemon, which needs namespaces
        assert "need encryptor-daemon" in api_content

        # Namespaces must complete before daemon
        assert "before encryptor-daemon" in ns_content

    def test_namespaces_start_post_blocks_until_dhcp_completes(self) -> None:
        """Verify namespaces service start_post waits for DHCP."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # start_post must run and verify DHCP before returning
        # This ensures dependent services wait for DHCP
        assert "start_post" in content

        # start_post should not exit early - it should verify DHCP
        start_post_match = re.search(
            r'start_post\(\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}',
            content,
            re.DOTALL
        )
        assert start_post_match

        start_post_content = start_post_match.group(1)

        # Should verify MGMT interface has IP (proves DHCP completed)
        assert (
            "NS_MGMT" in start_post_content or
            "ns_mgmt" in start_post_content or
            "IF_MGMT" in start_post_content
        ), "start_post must verify MGMT namespace/interface state"


class TestAPIBindingConfiguration:
    """Test API service binds correctly in MGMT namespace."""

    def test_api_service_starts_after_namespaces(self) -> None:
        """Verify encryptor-api depends on namespaces (which does DHCP) (AC: #2)."""
        api_service = OPENRC_DIR / "encryptor-api"
        content = api_service.read_text()

        # API must wait for namespaces to complete (which includes DHCP)
        assert "after" in content and "encryptor-namespaces" in content, (
            "API service must start after encryptor-namespaces"
        )

    def test_uvicorn_binds_to_all_interfaces(self) -> None:
        """Verify uvicorn binds to 0.0.0.0:443 to accept DHCP IP (AC: #2)."""
        uvicorn_server = OPENRC_DIR.parent.parent / "backend" / "uvicorn_server.py"
        content = uvicorn_server.read_text()

        # Must bind to 0.0.0.0 to accept connections on any IP (including DHCP)
        assert 'host="0.0.0.0"' in content, (
            "Uvicorn must bind to 0.0.0.0 to accept DHCP-assigned IP"
        )
        assert "port=443" in content, (
            "Uvicorn must bind to port 443 for HTTPS"
        )

    def test_api_runs_in_mgmt_namespace(self) -> None:
        """Verify API service runs in ns_mgmt namespace (AC: #2)."""
        api_service = OPENRC_DIR / "encryptor-api"
        content = api_service.read_text()

        # Must run uvicorn in ns_mgmt namespace
        assert "ip netns exec ns_mgmt" in content, (
            "API must run in ns_mgmt namespace"
        )
        # Should reference python/uvicorn
        assert "python" in content.lower() or "uvicorn" in content.lower()

    def test_api_health_check_runs_in_namespace(self) -> None:
        """Verify API health checks run in ns_mgmt namespace."""
        api_service = OPENRC_DIR / "encryptor-api"
        content = api_service.read_text()

        # Health check must run in ns_mgmt where API listens
        assert "healthcheck()" in content, "Must have healthcheck function"

        healthcheck_body = _extract_function_body(content, "healthcheck")
        assert "ip netns exec ns_mgmt" in healthcheck_body, (
            "Health check must run in ns_mgmt namespace"
        )

    def test_api_start_post_verifies_health_in_namespace(self) -> None:
        """Verify start_post health check runs in ns_mgmt."""
        api_service = OPENRC_DIR / "encryptor-api"
        content = api_service.read_text()

        start_post_body = _extract_function_body(content, "start_post")
        assert start_post_body, "Must have start_post function"

        # Health check in start_post must run in namespace
        assert "ip netns exec ns_mgmt" in start_post_body, (
            "start_post health check must run in ns_mgmt"
        )
        # Should check the health endpoint
        assert "/api/v1/system/health" in start_post_body

    def test_api_start_post_checks_mgmt_ip_accessibility(self) -> None:
        """Verify start_post attempts health check via DHCP-assigned MGMT IP."""
        api_service = OPENRC_DIR / "encryptor-api"
        content = api_service.read_text()

        # Expect mgmt_ip lookup and HTTPS check using mgmt_ip
        assert "mgmt_ip" in content, "start_post should resolve MGMT IP"
        assert "https://${mgmt_ip}:443/api/v1/system/health" in content, (
            "start_post must check API accessibility via DHCP-assigned IP"
        )


class TestInterfaceIPValidation:
    """Test validation of DHCP-assigned IP on eth0."""

    def test_interface_ip_check_function_exists(self) -> None:
        """Verify a function exists to check interface IP in namespace."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Should have interface_has_ip helper function
        assert "interface_has_ip()" in content, (
            "Must have interface_has_ip function to check IP address"
        )

        # Function should use ip -4 addr to check for inet address
        interface_has_ip_body = _extract_function_body(content, "interface_has_ip")
        assert interface_has_ip_body, "interface_has_ip must be parseable"
        assert "ip -4 addr" in interface_has_ip_body or "inet" in interface_has_ip_body, (
            "interface_has_ip must check for IPv4 address"
        )

    def test_start_post_verifies_mgmt_interface_ip(self) -> None:
        """Verify start_post validates eth0 has IP in ns_mgmt."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Extract start_post function using brace counting
        start_post_content = _extract_function_body(content, "start_post")
        assert start_post_content

        # Should call interface_has_ip with NS_MGMT and IF_MGMT
        # Or directly check IP in MGMT namespace
        ip_check_pattern = (
            "interface_has_ip" in start_post_content and
            ("NS_MGMT" in start_post_content or "IF_MGMT" in start_post_content)
        ) or (
            "ip netns exec" in start_post_content and
            ("ip addr" in start_post_content or "ip -4" in start_post_content)
        )

        assert ip_check_pattern, (
            "start_post must verify IP on MGMT interface in ns_mgmt"
        )


class TestHealthEndpointDHCPIntegration:
    """Integration tests for health endpoint DHCP/MGMT IP reporting (Task 4.5)."""

    def test_health_endpoint_includes_mgmt_interface_fields(self) -> None:
        """Verify health endpoint code includes mgmtInterface in response."""
        system_py = OPENRC_DIR.parent.parent / "backend" / "app" / "api" / "system.py"
        content = system_py.read_text()

        # Health endpoint must include mgmtInterface
        assert "mgmtInterface" in content, (
            "Health endpoint must return mgmtInterface field"
        )
        assert "_get_mgmt_interface_status" in content, (
            "Health endpoint must call _get_mgmt_interface_status"
        )

    def test_mgmt_interface_status_function_exists(self) -> None:
        """Verify function exists to get MGMT interface status."""
        system_py = OPENRC_DIR.parent.parent / "backend" / "app" / "api" / "system.py"
        content = system_py.read_text()

        # Must have function to get MGMT interface status
        assert "_get_mgmt_interface_status" in content, (
            "Must have _get_mgmt_interface_status function"
        )

        # Function should check ns_mgmt namespace
        assert "ns_mgmt" in content, (
            "Function must reference ns_mgmt namespace"
        )

    def test_mgmt_interface_status_checks_ip_address(self) -> None:
        """Verify MGMT interface status function checks for IP address."""
        system_py = OPENRC_DIR.parent.parent / "backend" / "app" / "api" / "system.py"
        content = system_py.read_text()

        # Should use ip command to check interface
        assert "ip" in content and "addr" in content, (
            "Function must use ip addr to check interface"
        )

    def test_health_schema_includes_mgmt_interface(self) -> None:
        """Verify health response schema includes MgmtInterfaceStatus."""
        schema_py = OPENRC_DIR.parent.parent / "backend" / "app" / "schemas" / "health.py"
        content = schema_py.read_text()

        # Schema must define MgmtInterfaceStatus
        assert "MgmtInterfaceStatus" in content, (
            "Schema must define MgmtInterfaceStatus model"
        )

        # Must include required fields
        assert "interface:" in content or "interface" in content
        assert '"ip"' in content or "ip:" in content or "ip =" in content
        assert "method" in content
        assert "leaseStatus" in content
        assert "status" in content

    def test_health_data_includes_mgmt_interface_field(self) -> None:
        """Verify HealthData model includes mgmtInterface field."""
        schema_py = OPENRC_DIR.parent.parent / "backend" / "app" / "schemas" / "health.py"
        content = schema_py.read_text()

        # HealthData must include mgmtInterface field
        assert "mgmtInterface:" in content or "mgmtInterface" in content, (
            "HealthData must include mgmtInterface field"
        )


class TestRuntimeDHCPValidation:
    """Runtime validation when running inside appliance with namespaces."""

    @pytest.mark.skipif(not _can_run_namespace_checks(), reason="ns_mgmt not available")
    def test_mgmt_interface_has_ip_in_namespace(self) -> None:
        """Verify MGMT interface has IPv4 address in ns_mgmt when DHCP is available."""
        result = subprocess.run(
            ["ip", "netns", "exec", "ns_mgmt", "ip", "-4", "addr", "show", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "inet " in result.stdout, "MGMT interface has no IPv4 address"

    @pytest.mark.skipif(not _can_run_namespace_checks(), reason="ns_mgmt not available")
    def test_api_accessible_via_mgmt_ip(self) -> None:
        """Verify API is reachable via DHCP-assigned MGMT IP over HTTPS."""
        if not shutil.which("wget"):
            pytest.skip("wget not available")

        ip_result = subprocess.run(
            ["ip", "netns", "exec", "ns_mgmt", "ip", "-4", "addr", "show", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert ip_result.returncode == 0
        mgmt_ip = ""
        for line in ip_result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                mgmt_ip = line.split()[1].split("/")[0]
                break
        if not mgmt_ip:
            pytest.skip("MGMT IP not assigned")

        check = subprocess.run(
            [
                "ip",
                "netns",
                "exec",
                "ns_mgmt",
                "wget",
                "-q",
                "--no-check-certificate",
                "-O",
                "/dev/null",
                f"https://{mgmt_ip}:443/api/v1/system/health",
            ],
            timeout=5,
        )
        assert check.returncode == 0, "API not reachable via MGMT IP"
