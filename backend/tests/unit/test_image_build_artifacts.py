"""
Unit tests for image build artifacts.

Validates the structure and content of files used to build
the qcow2 appliance image for CML deployment.
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

# Project paths
# test file is at: backend/tests/unit/test_image_build_artifacts.py
# Go up 4 levels to reach project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
IMAGE_DIR = PROJECT_ROOT / "image"


class TestBuildScript:
    """Tests for build-image.sh script."""

    @pytest.fixture
    def build_script(self) -> Path:
        return IMAGE_DIR / "build-image.sh"

    def test_build_script_exists(self, build_script: Path) -> None:
        """Build script exists at expected location."""
        assert build_script.exists(), f"build-image.sh not found at {build_script}"

    def test_build_script_executable_shebang(self, build_script: Path) -> None:
        """Build script has proper bash shebang."""
        content = build_script.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Script must start with bash shebang"

    def test_build_script_uses_strict_mode(self, build_script: Path) -> None:
        """Build script uses bash strict mode (set -euo pipefail)."""
        content = build_script.read_text()
        assert "set -euo pipefail" in content, "Script should use strict mode"

    def test_build_script_defines_alpine_version(self, build_script: Path) -> None:
        """Build script defines Alpine Linux 3.23.x version."""
        content = build_script.read_text()
        assert 'ALPINE_VERSION="3.23"' in content, "Must target Alpine 3.23"
        assert "ALPINE_RELEASE" in content, "Must define ALPINE_RELEASE"

    def test_build_script_defines_max_size(self, build_script: Path) -> None:
        """Build script enforces 500MB max compressed size."""
        content = build_script.read_text()
        assert "MAX_COMPRESSED_SIZE" in content, "Must define max compressed size"
        assert "500" in content, "Max size should be 500MB"

    def test_build_script_has_validation(self, build_script: Path) -> None:
        """Build script includes image validation step."""
        content = build_script.read_text()
        assert "validate_image" in content, "Must include validate_image function"

    def test_build_script_checks_required_host_tools(self, build_script: Path) -> None:
        """Build script checks for required host tools."""
        content = build_script.read_text()
        required_tools = [
            "losetup",
            "partprobe",
            "mount",
            "umount",
            "mountpoint",
            "tar",
            "gzip",
            "sha256sum",
            "extlinux",
        ]
        for tool in required_tools:
            assert tool in content, f"Missing dependency check for: {tool}"

    def test_build_script_installs_required_packages(self, build_script: Path) -> None:
        """Build script installs all required packages."""
        content = build_script.read_text()
        required_packages = [
            "python3",
            "strongswan",
            "nftables",
            "openrc",
            "iproute2",
        ]
        for pkg in required_packages:
            assert pkg in content, f"Must install package: {pkg}"

    def test_build_script_does_not_ignore_pip_failures(self, build_script: Path) -> None:
        """Build script must fail if backend dependency install fails."""
        content = build_script.read_text()
        assert "requirements.txt 2>/dev/null || true" not in content, (
            "Backend pip install must not ignore failures"
        )

    def test_build_script_validates_size_when_no_compress(self, build_script: Path) -> None:
        """Build script validates compressed size even when --no-compress is used."""
        content = build_script.read_text()
        assert "size-check.qcow2.gz" in content, "Must create temp gzip for size validation"

    def test_build_script_requires_ldlinux_module(self, build_script: Path) -> None:
        """Build script must ensure ldlinux.c32 is present for syslinux."""
        content = build_script.read_text()
        assert "ldlinux.c32" in content, "Build script must verify ldlinux.c32 exists"

    def test_build_script_uses_syslinux_compatible_ext4(self, build_script: Path) -> None:
        """Build script should disable ext4 features unsupported by syslinux."""
        content = build_script.read_text()
        assert "-O ^64bit,^metadata_csum" in content, (
            "mkfs.ext4 must disable 64bit and metadata_csum for syslinux compatibility"
        )

    def test_build_script_bash_syntax(self, build_script: Path) -> None:
        """Build script has valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", str(build_script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"


class TestValidationScript:
    """Tests for validate-image.sh script."""

    @pytest.fixture
    def validate_script(self) -> Path:
        return IMAGE_DIR / "validate-image.sh"

    def test_validation_script_exists(self, validate_script: Path) -> None:
        """Validation script exists at expected location."""
        assert validate_script.exists(), f"validate-image.sh not found at {validate_script}"

    def test_validation_script_shebang(self, validate_script: Path) -> None:
        """Validation script has proper bash shebang."""
        content = validate_script.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Script must start with bash shebang"


class TestCMLNodeDefinition:
    """Tests for CML node definition YAML."""

    @pytest.fixture
    def node_definition(self) -> Path:
        return IMAGE_DIR / "config" / "cml-node.yaml"

    def test_node_definition_exists(self, node_definition: Path) -> None:
        """CML node definition exists."""
        assert node_definition.exists(), "cml-node.yaml not found"

    def test_node_definition_valid_yaml(self, node_definition: Path) -> None:
        """CML node definition is valid YAML."""
        content = node_definition.read_text()
        try:
            data = yaml.safe_load(content)
            assert data is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_node_definition_has_required_fields(self, node_definition: Path) -> None:
        """CML node definition has all required fields."""
        data = yaml.safe_load(node_definition.read_text())

        required_fields = ["id", "label", "description", "interfaces", "resource_pool"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_node_definition_has_three_interfaces(self, node_definition: Path) -> None:
        """CML node definition defines 3 network interfaces."""
        data = yaml.safe_load(node_definition.read_text())

        interfaces = data.get("interfaces", [])
        assert len(interfaces) == 3, "Must define exactly 3 interfaces"

        # Verify interface labels
        labels = {iface["label"] for iface in interfaces}
        assert labels == {"MGMT", "CT", "PT"}, "Must have MGMT, CT, PT interfaces"

    def test_node_definition_resource_requirements(self, node_definition: Path) -> None:
        """CML node definition meets resource requirements (2 vCPU, 1GB min)."""
        data = yaml.safe_load(node_definition.read_text())

        resource_pool = data.get("resource_pool", {})

        # CPU requirements
        cpus = resource_pool.get("cpus", {})
        assert cpus.get("min", 0) >= 2, "Min vCPU must be >= 2"
        assert cpus.get("max", 0) <= 4, "Max vCPU should be <= 4"

        # Memory requirements
        memory = resource_pool.get("memory", {})
        assert memory.get("min", 0) >= 1024, "Min RAM must be >= 1024MB (1GB)"


class TestCMLRootNodeDefinition:
    """Tests for root-level CML node definition YAML."""

    @pytest.fixture
    def root_node_definition(self) -> Path:
        return PROJECT_ROOT / "encryptor-sim.node.yaml"

    def test_root_node_definition_exists(self, root_node_definition: Path) -> None:
        """Root-level CML node definition exists."""
        assert root_node_definition.exists(), "encryptor-sim.node.yaml not found"

    def test_root_node_definition_valid_yaml(self, root_node_definition: Path) -> None:
        """Root-level CML node definition is valid YAML."""
        content = root_node_definition.read_text()
        try:
            data = yaml.safe_load(content)
            assert data is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_root_node_definition_resources(self, root_node_definition: Path) -> None:
        """Root-level node definition meets 2 vCPU / 1GB minimum."""
        data = yaml.safe_load(root_node_definition.read_text())

        sim = data.get("sim", {}).get("linux_native", {})
        assert sim.get("cpus", 0) >= 2, "Min vCPU must be >= 2"
        assert sim.get("ram", 0) >= 1024, "Min RAM must be >= 1024MB (1GB)"

    def test_root_node_definition_interfaces(self, root_node_definition: Path) -> None:
        """Root-level node definition lists MGMT/CT/PT interfaces."""
        data = yaml.safe_load(root_node_definition.read_text())
        interfaces = data.get("device", {}).get("interfaces", {}).get("physical", [])
        assert interfaces == ["MGMT", "CT", "PT"], "Interface order must be MGMT, CT, PT"

class TestOpenRCServices:
    """Tests for OpenRC service definitions."""

    @pytest.fixture
    def openrc_dir(self) -> Path:
        return IMAGE_DIR / "openrc"

    def test_openrc_services_exist(self, openrc_dir: Path) -> None:
        """All required OpenRC services exist."""
        required_services = [
            "encryptor-namespaces",
            "encryptor-strongswan",
            "encryptor-daemon",
            "encryptor-api",
        ]
        for service in required_services:
            service_path = openrc_dir / service
            assert service_path.exists(), f"Service not found: {service}"

    def test_openrc_services_have_shebang(self, openrc_dir: Path) -> None:
        """OpenRC services have correct shebang."""
        for service_file in openrc_dir.iterdir():
            if service_file.is_file():
                content = service_file.read_text()
                assert content.startswith("#!/sbin/openrc-run"), (
                    f"{service_file.name} must start with #!/sbin/openrc-run"
                )

    def test_namespace_service_runs_first(self, openrc_dir: Path) -> None:
        """Namespace service is configured to run before others."""
        service = openrc_dir / "encryptor-namespaces"
        content = service.read_text()
        assert "before encryptor-daemon" in content, "Namespaces must run before daemon"

    def test_namespace_service_creates_veth_pair(self, openrc_dir: Path) -> None:
        """Namespace service creates veth pair for xfrm routing."""
        service = openrc_dir / "encryptor-namespaces"
        content = service.read_text()
        assert "veth_ct_default" in content, "Must create veth_ct_default"
        assert "veth_ct_pt" in content, "Must create veth_ct_pt"
        assert "169.254.0.1/30" in content, "Must assign link-local IP to default side"
        assert "169.254.0.2/30" in content, "Must assign link-local IP to ns_pt side"

    def test_daemon_service_depends_on_namespaces(self, openrc_dir: Path) -> None:
        """Daemon service depends on namespace service."""
        service = openrc_dir / "encryptor-daemon"
        content = service.read_text()
        assert "need encryptor-namespaces" in content, "Daemon must need namespaces"

    def test_api_service_depends_on_daemon(self, openrc_dir: Path) -> None:
        """API service depends on daemon service."""
        service = openrc_dir / "encryptor-api"
        content = service.read_text()
        assert "need encryptor-daemon" in content, "API must need daemon"


class TestNetworkInterfaces:
    """Tests for network interface configuration."""

    @pytest.fixture
    def interfaces_file(self) -> Path:
        return IMAGE_DIR / "rootfs" / "etc" / "network" / "interfaces"

    def test_interfaces_file_exists(self, interfaces_file: Path) -> None:
        """Network interfaces file exists."""
        assert interfaces_file.exists(), "interfaces file not found"

    def test_interfaces_defines_eth0_manual(self, interfaces_file: Path) -> None:
        """eth0 (MGMT) is manual in root namespace; DHCP runs in ns_mgmt."""
        content = interfaces_file.read_text()
        assert "iface eth0 inet manual" in content, "eth0 must be manual in root namespace"

    def test_interfaces_defines_eth1_manual(self, interfaces_file: Path) -> None:
        """eth1 (CT) is configured as manual."""
        content = interfaces_file.read_text()
        assert "iface eth1 inet manual" in content, "eth1 must be manual"

    def test_interfaces_defines_eth2_manual(self, interfaces_file: Path) -> None:
        """eth2 (PT) is configured as manual."""
        content = interfaces_file.read_text()
        assert "iface eth2 inet manual" in content, "eth2 must be manual"

    def test_interfaces_auto_starts(self, interfaces_file: Path) -> None:
        """All interfaces are set to auto-start."""
        content = interfaces_file.read_text()
        assert "auto eth0" in content, "eth0 must auto-start"
        assert "auto eth1" in content, "eth1 must auto-start"
        assert "auto eth2" in content, "eth2 must auto-start"


class TestRootfsOverlay:
    """Tests for rootfs overlay structure."""

    @pytest.fixture
    def rootfs_dir(self) -> Path:
        return IMAGE_DIR / "rootfs"

    def test_hostname_file_exists(self, rootfs_dir: Path) -> None:
        """Hostname file exists in rootfs overlay."""
        hostname_file = rootfs_dir / "etc" / "hostname"
        assert hostname_file.exists(), "hostname file not found"

    def test_hostname_is_encryptor_sim(self, rootfs_dir: Path) -> None:
        """Hostname is set to encryptor-sim."""
        hostname_file = rootfs_dir / "etc" / "hostname"
        content = hostname_file.read_text().strip()
        assert content == "encryptor-sim", f"Hostname should be 'encryptor-sim', got '{content}'"
