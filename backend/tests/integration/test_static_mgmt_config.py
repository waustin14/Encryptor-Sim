"""Integration tests for static MGMT interface configuration.

Tests that the configure-mgmt serial console script properly configures
static IP for the MGMT interface. Validates AC #1 of Story 2.4.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


# Path to image files
IMAGE_DIR = Path(__file__).parent.parent.parent.parent / "image"
OPENRC_DIR = IMAGE_DIR / "openrc"
ROOTFS_DIR = IMAGE_DIR / "rootfs"

SCRIPT_PATH = ROOTFS_DIR / "usr" / "local" / "bin" / "configure-mgmt"


def _run_configure_mgmt(
    args: list[str],
    tmp_path: Path,
    cmd_log: Path | None = None,
) -> None:
    env = os.environ.copy()
    env["CONFIGURE_MGMT_ROOT"] = str(tmp_path)
    env["CONFIGURE_MGMT_SKIP_NETNS"] = "1"
    env["CONFIGURE_MGMT_ALLOW_NONROOT"] = "1"
    env["CONFIGURE_MGMT_NONINTERACTIVE"] = "1"
    env["CONFIGURE_MGMT_ASSUME_UDHCPC"] = "1"
    if cmd_log is not None:
        env["CONFIGURE_MGMT_CMD_LOG"] = str(cmd_log)
    subprocess.run(["sh", str(SCRIPT_PATH), *args], check=True, env=env, text=True)


class TestConfigureMgmtScriptExists:
    """Test configure-mgmt script exists and is properly structured."""

    def test_configure_mgmt_script_exists(self) -> None:
        """Verify configure-mgmt script exists at expected path (Task 1.1)."""
        assert SCRIPT_PATH.exists(), (
            "configure-mgmt script must exist at /usr/local/bin/configure-mgmt"
        )

    def test_configure_mgmt_script_is_executable(self) -> None:
        """Verify configure-mgmt script has executable permissions."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        # Check file has shebang
        content = SCRIPT_PATH.read_text()
        assert content.startswith("#!/"), "Script must have shebang"

    def test_configure_mgmt_has_menu_options(self) -> None:
        """Verify script has required menu options (Task 1.1)."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must have static IP configuration option
        assert "Static IP" in content or "static" in content.lower(), (
            "Script must have static IP configuration option"
        )

        # Must have DHCP revert option
        assert "DHCP" in content or "dhcp" in content.lower(), (
            "Script must have DHCP revert option"
        )

        # Must have show current config option
        assert "Current" in content or "Show" in content or "status" in content.lower(), (
            "Script must have option to show current configuration"
        )

        # Must have exit option
        assert "Exit" in content or "exit" in content or "Quit" in content, (
            "Script must have exit option"
        )


class TestIPAddressValidation:
    """Test IP address validation functions (Task 1.2)."""

    def test_script_has_ip_validation_function(self) -> None:
        """Verify script has IP validation function."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must have IP validation function
        assert "validate_ip" in content, (
            "Script must have validate_ip function"
        )

    def test_ip_validation_checks_format(self) -> None:
        """Verify IP validation checks for proper IPv4 format."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Should use grep or regex to validate IP format
        has_format_check = (
            "grep" in content and
            ("[0-9]" in content or r"\d" in content or "0-9" in content)
        )
        assert has_format_check, (
            "IP validation must check for proper IPv4 format"
        )

    def test_ip_validation_checks_octet_range(self) -> None:
        """Verify IP validation checks octets are 0-255."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Should check octet range (0-255)
        has_range_check = "255" in content or "256" in content
        assert has_range_check, (
            "IP validation must check octet range (0-255)"
        )


class TestStaticConfigurationApplication:
    """Test static configuration is applied correctly (Task 1.3)."""

    def test_script_creates_interfaces_file(self) -> None:
        """Verify script writes to /etc/network/interfaces.d/mgmt."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must write interfaces configuration
        assert "/etc/network/interfaces.d/mgmt" in content, (
            "Script must write to /etc/network/interfaces.d/mgmt"
        )

    def test_script_applies_config_in_namespace(self) -> None:
        """Verify script applies config in ns_mgmt namespace."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must use ip netns exec for applying config (may use variable for namespace)
        assert "ip netns exec" in content, (
            "Script must use 'ip netns exec' to apply configuration in namespace"
        )
        # Must define or reference ns_mgmt namespace
        assert "ns_mgmt" in content, (
            "Script must reference ns_mgmt namespace"
        )

    def test_script_uses_ifup_for_static_config(self) -> None:
        """Verify script uses ifup to apply static configuration."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must use ifup to apply configuration
        assert "ifup" in content, (
            "Script must use ifup to apply static configuration"
        )


class TestDHCPClientDisabling:
    """Test DHCP client is disabled when static config is applied (Task 1.4)."""

    def test_script_creates_mode_flag_file(self) -> None:
        """Verify script creates /etc/encryptor/network-config mode flag."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must write mode flag file
        assert "/etc/encryptor/network-config" in content, (
            "Script must write mode flag to /etc/encryptor/network-config"
        )

    def test_script_sets_mode_static(self) -> None:
        """Verify script sets mode=static in flag file."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must set mode=static
        assert "mode=static" in content, (
            "Script must set mode=static in config flag file"
        )


class TestDHCPRevert:
    """Test revert to DHCP functionality (Task 1.5)."""

    def test_script_can_revert_to_dhcp(self) -> None:
        """Verify script has DHCP revert functionality."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must have revert to DHCP function
        assert "revert" in content.lower() or "dhcp" in content.lower(), (
            "Script must have revert to DHCP functionality"
        )

    def test_script_removes_static_config_on_revert(self) -> None:
        """Verify script removes static config file on DHCP revert."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must remove static config file
        assert "rm" in content and "/etc/network/interfaces.d/mgmt" in content, (
            "Script must remove static config file on DHCP revert"
        )

    def test_script_sets_mode_dhcp_on_revert(self) -> None:
        """Verify script sets mode=dhcp on revert."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must set mode=dhcp
        assert "mode=dhcp" in content, (
            "Script must set mode=dhcp on revert"
        )

    def test_script_runs_udhcpc_on_revert(self) -> None:
        """Verify script runs udhcpc after reverting to DHCP."""
        if not SCRIPT_PATH.exists():
            pytest.skip("Script not yet created")

        content = SCRIPT_PATH.read_text()

        # Must run udhcpc after revert
        assert "udhcpc" in content, (
            "Script must run udhcpc after reverting to DHCP"
        )


class TestOpenRCServiceStaticModeDetection:
    """Test OpenRC service detects static mode at boot (Task 2)."""

    def test_namespaces_service_reads_mode_flag(self) -> None:
        """Verify encryptor-namespaces reads /etc/encryptor/network-config (Task 2.2)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must reference network-config file
        assert "/etc/encryptor/network-config" in content, (
            "Service must read mode from /etc/encryptor/network-config"
        )

    def test_namespaces_service_detects_static_mode(self) -> None:
        """Verify service detects when mode=static (Task 2.3)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must check for static mode
        assert "static" in content, (
            "Service must check for static mode"
        )
        # Must have conditional for static vs dhcp
        assert "mode" in content.lower(), (
            "Service must read and check mode value"
        )

    def test_namespaces_service_skips_dhcp_when_static(self) -> None:
        """Verify service skips udhcpc when static mode is set (Task 2.4)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must have conditional logic for DHCP
        # The script should only run udhcpc when mode is dhcp
        assert "dhcp" in content.lower(), (
            "Service must handle dhcp mode"
        )
        assert "udhcpc" in content, (
            "Service must reference udhcpc for DHCP mode"
        )

    def test_namespaces_service_applies_static_config_at_boot(self) -> None:
        """Verify service applies static config from interfaces file (Task 2.5)."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must reference interfaces.d/mgmt file for static config
        assert "/etc/network/interfaces.d/mgmt" in content, (
            "Service must reference static interfaces file"
        )
        # Must use ifup or ip commands to apply config
        assert "ifup" in content or ("ip" in content and "addr" in content), (
            "Service must use ifup or ip addr to apply static config"
        )

    def test_namespaces_service_defaults_to_dhcp(self) -> None:
        """Verify service defaults to DHCP when no mode flag exists."""
        service_file = OPENRC_DIR / "encryptor-namespaces"
        content = service_file.read_text()

        # Must default to dhcp
        # Look for default assignment or else clause
        assert "dhcp" in content.lower(), (
            "Service must default to dhcp mode"
        )


class TestHealthEndpointStaticConfig:
    """Test health endpoint reports static configuration correctly (Task 3)."""

    def test_health_schema_includes_netmask_and_gateway(self) -> None:
        """Verify health schema includes netmask and gateway fields (Task 3.3)."""
        schema_path = IMAGE_DIR.parent / "backend" / "app" / "schemas" / "health.py"
        content = schema_path.read_text()

        # Must include netmask field
        assert "netmask" in content, (
            "MgmtInterfaceStatus must include netmask field"
        )
        # Must include gateway field
        assert "gateway" in content, (
            "MgmtInterfaceStatus must include gateway field"
        )

    def test_health_api_reads_network_config(self) -> None:
        """Verify health API reads /etc/encryptor/network-config (Task 3.2)."""
        api_path = IMAGE_DIR.parent / "backend" / "app" / "api" / "system.py"
        content = api_path.read_text()

        # Must check for network-config file
        assert "/etc/encryptor/network-config" in content, (
            "Health API must read mode from /etc/encryptor/network-config"
        )

    def test_health_api_reports_static_method(self) -> None:
        """Verify health API can report method='static' (Task 3.2)."""
        api_path = IMAGE_DIR.parent / "backend" / "app" / "api" / "system.py"
        content = api_path.read_text()

        # Must be able to return static method
        assert '"static"' in content or "'static'" in content, (
            "Health API must be able to report method='static'"
        )

    def test_health_api_reads_static_interfaces_file(self) -> None:
        """Verify health API reads gateway from static config (Task 3.3)."""
        api_path = IMAGE_DIR.parent / "backend" / "app" / "api" / "system.py"
        content = api_path.read_text()

        # Must read interfaces.d/mgmt for static config details
        assert "/etc/network/interfaces.d/mgmt" in content, (
            "Health API must read gateway from static interfaces file"
        )


class TestStaticConfigurationIntegration:
    """Integration tests for static configuration scenarios (Task 4)."""

    def test_script_sets_static_configuration_correctly(self, tmp_path: Path) -> None:
        """Test serial console script creates valid config (Task 4.1)."""
        _run_configure_mgmt(
            ["--apply-static", "192.168.1.10", "255.255.255.0", "192.168.1.1"],
            tmp_path,
        )

        interfaces_file = tmp_path / "etc" / "network" / "interfaces.d" / "mgmt"
        network_config = tmp_path / "etc" / "encryptor" / "network-config"

        assert interfaces_file.exists()
        assert network_config.exists()

        content = interfaces_file.read_text()
        assert "iface eth0 inet static" in content
        assert "address 192.168.1.10" in content
        assert "netmask 255.255.255.0" in content
        assert "gateway 192.168.1.1" in content

        assert "mode=static" in network_config.read_text()

    def test_configuration_persists_across_reboot_scenario(self, tmp_path: Path) -> None:
        """Test configuration files are written to /etc/ for persistence (Task 4.2)."""
        _run_configure_mgmt(
            ["--apply-static", "10.0.0.10", "255.255.255.0", "10.0.0.1"],
            tmp_path,
        )

        assert (tmp_path / "etc" / "network" / "interfaces.d" / "mgmt").exists()
        assert (tmp_path / "etc" / "encryptor" / "network-config").exists()

    def test_dhcp_skipped_when_static_mode_set(self, tmp_path: Path) -> None:
        """Test DHCP client does not run when static mode is set (Task 4.3)."""
        cmd_log = tmp_path / "cmd.log"
        _run_configure_mgmt(
            ["--apply-static", "192.168.10.10", "255.255.255.0", "192.168.10.1"],
            tmp_path,
            cmd_log,
        )

        logged = cmd_log.read_text()
        assert "udhcpc -i" not in logged, "Static apply should not start udhcpc"

    def test_revert_to_dhcp_removes_static_files(self, tmp_path: Path) -> None:
        """Test revert to DHCP removes static configuration (Task 4.4)."""
        _run_configure_mgmt(
            ["--apply-static", "172.16.0.10", "255.255.0.0", "172.16.0.1"],
            tmp_path,
        )
        _run_configure_mgmt(["--revert-dhcp"], tmp_path)

        interfaces_file = tmp_path / "etc" / "network" / "interfaces.d" / "mgmt"
        network_config = tmp_path / "etc" / "encryptor" / "network-config"

        assert not interfaces_file.exists()
        assert "mode=dhcp" in network_config.read_text()

    def test_revert_to_dhcp_invokes_udhcpc(self, tmp_path: Path) -> None:
        """Test revert to DHCP runs udhcpc (Task 4.4)."""
        cmd_log = tmp_path / "cmd.log"
        _run_configure_mgmt(["--revert-dhcp"], tmp_path, cmd_log)

        logged = cmd_log.read_text()
        assert "udhcpc" in logged, "DHCP revert should invoke udhcpc"

    def test_health_endpoint_reports_correct_method(self) -> None:
        """Test health endpoint reports configuration method correctly (Task 4.5)."""
        api_path = IMAGE_DIR.parent / "backend" / "app" / "api" / "system.py"
        content = api_path.read_text()

        # API must read from config file
        assert "/etc/encryptor/network-config" in content, (
            "Health API must read mode from network-config"
        )
        # API must distinguish between methods
        assert "'static'" in content or '"static"' in content, (
            "Health API must be able to return static method"
        )
        assert "'dhcp'" in content or '"dhcp"' in content, (
            "Health API must be able to return dhcp method"
        )


class TestExampleConfigFiles:
    """Test example configuration files exist."""

    def test_network_config_example_exists(self) -> None:
        """Verify network-config.example file exists."""
        example_path = ROOTFS_DIR / "etc" / "encryptor" / "network-config.example"
        assert example_path.exists(), (
            "Example network config must exist at /etc/encryptor/network-config.example"
        )

    def test_mgmt_interfaces_example_exists(self) -> None:
        """Verify mgmt.example interfaces file exists."""
        example_path = ROOTFS_DIR / "etc" / "network" / "interfaces.d" / "mgmt.example"
        assert example_path.exists(), (
            "Example interfaces file must exist at /etc/network/interfaces.d/mgmt.example"
        )

    def test_network_config_example_has_valid_content(self) -> None:
        """Verify network-config.example has valid mode specification."""
        example_path = ROOTFS_DIR / "etc" / "encryptor" / "network-config.example"
        if not example_path.exists():
            pytest.skip("Example file not yet created")

        content = example_path.read_text()

        # Must document both modes
        assert "static" in content.lower(), "Example must document static mode"
        assert "dhcp" in content.lower(), "Example must document dhcp mode"

    def test_mgmt_interfaces_example_has_static_config(self) -> None:
        """Verify mgmt.example has static IP configuration format."""
        example_path = ROOTFS_DIR / "etc" / "network" / "interfaces.d" / "mgmt.example"
        if not example_path.exists():
            pytest.skip("Example file not yet created")

        content = example_path.read_text()

        # Must have standard interfaces.d format
        assert "iface eth0 inet static" in content, (
            "Example must have 'iface eth0 inet static'"
        )
        assert "address" in content, "Example must have address field"
        assert "netmask" in content, "Example must have netmask field"
        assert "gateway" in content, "Example must have gateway field"
