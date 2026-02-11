"""Unit tests for daemon network operations (Story 4.1, Tasks 2-3).

Tests verify interface configuration, validation, isolation verification,
and persistent config file generation.
"""

import subprocess
from unittest.mock import MagicMock, call

import pytest

from backend.daemon.ops.network_ops import (
    INTERFACE_MAP,
    _netmask_to_prefix,
    configure_interface,
    get_interface_stats,
    validate_interface_config,
    verify_isolation_after_config,
    write_netns_config,
)


# ---------------------------------------------------------------------------
# Task 2.3: IP address validation in daemon
# ---------------------------------------------------------------------------


class TestValidateInterfaceConfig:
    """Tests for daemon-side input validation (defense-in-depth)."""

    def test_valid_ct_config(self):
        """Validate accepted CT interface configuration."""
        validate_interface_config("CT", "192.168.10.1", "255.255.255.0", "192.168.10.254")

    def test_valid_pt_config(self):
        """Validate accepted PT interface configuration."""
        validate_interface_config("PT", "10.0.0.1", "255.255.255.0", "10.0.0.254")

    def test_valid_mgmt_config(self):
        """Validate accepted MGMT interface configuration."""
        validate_interface_config("MGMT", "192.168.1.100", "255.255.255.0", "192.168.1.1")

    def test_unknown_interface_raises(self):
        """Reject unknown interface name."""
        with pytest.raises(ValueError, match="Unknown interface"):
            validate_interface_config("WAN", "10.0.0.1", "255.255.255.0", "10.0.0.254")

    def test_invalid_ip_raises(self):
        """Reject invalid IP address."""
        with pytest.raises(ValueError, match="Invalid IP address"):
            validate_interface_config("CT", "999.999.999.999", "255.255.255.0", "10.0.0.254")

    def test_reserved_ip_zero_raises(self):
        """Reject 0.0.0.0 as reserved."""
        with pytest.raises(ValueError, match="Reserved IP"):
            validate_interface_config("CT", "0.0.0.0", "255.255.255.0", "10.0.0.254")

    def test_broadcast_ip_raises(self):
        """Reject 255.255.255.255 as broadcast."""
        with pytest.raises(ValueError, match="Reserved IP"):
            validate_interface_config("CT", "255.255.255.255", "255.255.255.0", "10.0.0.254")

    def test_invalid_netmask_raises(self):
        """Reject invalid netmask."""
        with pytest.raises(ValueError, match="Invalid netmask"):
            validate_interface_config("CT", "10.0.0.1", "999.0.0.0", "10.0.0.254")

    def test_invalid_gateway_raises(self):
        """Reject invalid gateway address."""
        with pytest.raises(ValueError, match="Invalid gateway"):
            validate_interface_config("CT", "10.0.0.1", "255.255.255.0", "invalid")

    def test_gateway_not_in_subnet_raises(self):
        """Reject gateway outside the configured subnet."""
        with pytest.raises(ValueError, match="not in subnet"):
            validate_interface_config("CT", "192.168.10.1", "255.255.255.0", "10.0.0.254")

    def test_case_insensitive_name(self):
        """Accept lowercase interface names."""
        validate_interface_config("ct", "10.0.0.1", "255.255.255.0", "10.0.0.254")


class TestNetmaskToPrefix:
    """Tests for netmask to CIDR prefix conversion."""

    def test_class_c(self):
        assert _netmask_to_prefix("255.255.255.0") == 24

    def test_class_b(self):
        assert _netmask_to_prefix("255.255.0.0") == 16

    def test_class_a(self):
        assert _netmask_to_prefix("255.0.0.0") == 8

    def test_slash_25(self):
        assert _netmask_to_prefix("255.255.255.128") == 25


# ---------------------------------------------------------------------------
# Task 2.1, 2.2: Daemon configure_interface command
# ---------------------------------------------------------------------------


class TestConfigureInterface:
    """Tests for configure_interface with mocked runner (Task 2.1, 2.2)."""

    def _make_runner(self):
        """Create a mock runner that succeeds for all commands."""
        runner = MagicMock()
        runner.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        return runner

    def test_configure_ct_calls_correct_namespace(self, tmp_path):
        """Verify CT config uses ns_ct namespace."""
        runner = self._make_runner()
        result = configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        assert result["namespace"] == "ns_ct"
        assert result["device"] == "eth1"
        assert result["status"] == "success"

        # Verify namespace was used in ip commands
        calls = runner.call_args_list
        for c in calls:
            args = c[0][0]
            if "ip" in args and "netns" in args:
                assert "ns_ct" in args

    def test_configure_pt_calls_correct_namespace(self, tmp_path):
        """Verify PT config uses ns_pt namespace."""
        runner = self._make_runner()
        result = configure_interface(
            "PT", "10.0.0.1", "255.255.255.0", "10.0.0.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        assert result["namespace"] == "ns_pt"
        assert result["device"] == "eth2"

    def test_configure_pt_adds_default_ns_route(self, tmp_path):
        """Verify PT config adds a route for the PT subnet in the default namespace."""
        runner = self._make_runner()
        configure_interface(
            "PT", "10.0.0.1", "255.255.255.0", "10.0.0.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        calls = runner.call_args_list
        # Find the route replace call in the default namespace (no "netns exec")
        pt_route_calls = [
            c for c in calls
            if "route" in c[0][0] and "replace" in c[0][0]
            and "10.0.0.0/24" in c[0][0] and "169.254.0.2" in c[0][0]
        ]
        assert len(pt_route_calls) == 1

    def test_configure_ct_does_not_add_pt_route(self, tmp_path):
        """Verify CT config does NOT add a PT subnet route."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        calls = runner.call_args_list
        pt_route_calls = [
            c for c in calls
            if "route" in c[0][0] and "replace" in c[0][0]
            and "169.254.0.2" in c[0][0]
        ]
        assert len(pt_route_calls) == 0

    def test_configure_mgmt_calls_correct_namespace(self, tmp_path):
        """Verify MGMT config uses ns_mgmt namespace."""
        runner = self._make_runner()
        result = configure_interface(
            "MGMT", "192.168.1.100", "255.255.255.0", "192.168.1.1",
            runner=runner, config_base_dir=str(tmp_path),
        )
        assert result["namespace"] == "ns_mgmt"
        assert result["device"] == "eth0"

    def test_configure_flushes_before_adding(self, tmp_path):
        """Verify existing config is flushed before applying new config."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        first_call_args = runner.call_args_list[0][0][0]
        assert "flush" in first_call_args

    def test_configure_adds_ip_with_correct_prefix(self, tmp_path):
        """Verify IP address is added with correct CIDR prefix."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        calls = runner.call_args_list
        addr_add_call = [c for c in calls if "add" in c[0][0] and "addr" in c[0][0]]
        assert len(addr_add_call) > 0
        assert "192.168.10.1/24" in addr_add_call[0][0][0]

    def test_configure_brings_interface_up(self, tmp_path):
        """Verify interface is brought up after configuration."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        calls = runner.call_args_list
        link_up_calls = [c for c in calls if "up" in c[0][0] and "link" in c[0][0]]
        assert len(link_up_calls) > 0

    def test_configure_sets_default_gateway(self, tmp_path):
        """Verify default gateway is set."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        calls = runner.call_args_list
        route_calls = [
            c for c in calls
            if "route" in c[0][0] and "add" in c[0][0] and "default" in c[0][0]
        ]
        assert len(route_calls) > 0
        assert "192.168.10.254" in route_calls[0][0][0]

    def test_configure_returns_success_dict(self, tmp_path):
        """Verify return value structure."""
        runner = self._make_runner()
        result = configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        assert result["status"] == "success"
        assert "message" in result
        assert result["ip_address"] == "192.168.10.1"

    def test_configure_writes_persistent_config(self, tmp_path):
        """Verify persistent config file is written (Task 3.2)."""
        runner = self._make_runner()
        configure_interface(
            "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            runner=runner, config_base_dir=str(tmp_path),
        )
        config_file = tmp_path / "ns_ct" / "network" / "eth1"
        assert config_file.exists()
        content = config_file.read_text()
        assert "192.168.10.1/24" in content

    def test_configure_raises_on_subprocess_failure(self):
        """Verify CalledProcessError propagates from failed commands."""
        runner = MagicMock()
        runner.side_effect = subprocess.CalledProcessError(1, "ip")
        with pytest.raises(subprocess.CalledProcessError):
            configure_interface(
                "CT", "192.168.10.1", "255.255.255.0", "192.168.10.254",
                runner=runner,
            )

    def test_configure_validates_before_executing(self):
        """Verify validation runs before any commands."""
        runner = self._make_runner()
        with pytest.raises(ValueError, match="Invalid IP"):
            configure_interface(
                "CT", "999.999.999.999", "255.255.255.0", "10.0.0.254",
                runner=runner,
            )
        runner.assert_not_called()


# ---------------------------------------------------------------------------
# Task 2.4: Namespace isolation verification
# ---------------------------------------------------------------------------


class TestVerifyIsolationAfterConfig:
    """Tests for isolation verification after configuration (Task 2.4)."""

    def test_isolation_passes_when_rules_present(self):
        """Verify pass when nftables rules contain policy drop."""
        runner = MagicMock()
        runner.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="chain forward { policy drop; }"
        )
        result = verify_isolation_after_config(runner=runner)
        assert result["status"] == "pass"

    def test_isolation_fails_when_nft_command_fails(self):
        """Verify fail when nft list command returns non-zero."""
        runner = MagicMock()
        runner.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=""
        )
        result = verify_isolation_after_config(runner=runner)
        assert result["status"] == "fail"
        assert "missing" in result["message"]

    def test_isolation_fails_when_policy_not_drop(self):
        """Verify fail when forward policy is not drop."""
        runner = MagicMock()
        runner.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="chain forward { policy accept; }"
        )
        result = verify_isolation_after_config(runner=runner)
        assert result["status"] == "fail"
        assert "policy" in result["message"]

    def test_isolation_checks_default_and_ns_pt(self):
        """Verify both default and ns_pt namespaces are checked."""
        runner = MagicMock()
        runner.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="chain forward { policy drop; }"
        )
        verify_isolation_after_config(runner=runner)
        calls = runner.call_args_list
        # First call should be for default namespace (no "ip netns exec")
        assert calls[0][0][0][0] == "nft"
        # Second call should be for ns_pt namespace
        assert "ns_pt" in calls[1][0][0]


# ---------------------------------------------------------------------------
# Task 2.5: IPC command handler
# ---------------------------------------------------------------------------


class TestConfigureInterfaceCommand:
    """Tests for handle_command('configure_interface') (Task 2.5)."""

    def test_command_requires_payload(self):
        from backend.daemon.ipc.commands import CommandError, handle_command

        with pytest.raises(CommandError, match="requires payload"):
            handle_command("configure_interface", None)

    def test_command_requires_all_fields(self):
        from backend.daemon.ipc.commands import CommandError, handle_command

        with pytest.raises(CommandError, match="Missing required"):
            handle_command("configure_interface", {"namespace": "ns_ct"})

    def test_command_rejects_unknown_namespace(self):
        from backend.daemon.ipc.commands import CommandError, handle_command

        with pytest.raises(CommandError, match="Unknown namespace"):
            handle_command("configure_interface", {
                "namespace": "ns_unknown",
                "device": "eth1",
                "ip_address": "10.0.0.1",
                "netmask": "255.255.255.0",
                "gateway": "10.0.0.254",
            })


# ---------------------------------------------------------------------------
# Task 3.2: Persistent network config file generation
# ---------------------------------------------------------------------------


class TestWriteNetnsConfig:
    """Tests for persistent network config file generation (Task 3.2)."""

    def test_creates_config_file(self, tmp_path):
        """Verify config file is created at correct path."""
        config_path = write_netns_config(
            "ns_ct", "eth1", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            base_dir=str(tmp_path),
        )
        assert config_path.exists()
        assert config_path == tmp_path / "ns_ct" / "network" / "eth1"

    def test_config_contains_correct_address(self, tmp_path):
        """Verify config file contains the correct IP address."""
        config_path = write_netns_config(
            "ns_ct", "eth1", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            base_dir=str(tmp_path),
        )
        content = config_path.read_text()
        assert "192.168.10.1/24" in content

    def test_config_contains_gateway(self, tmp_path):
        """Verify config file contains the gateway."""
        config_path = write_netns_config(
            "ns_ct", "eth1", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            base_dir=str(tmp_path),
        )
        content = config_path.read_text()
        assert "gateway 192.168.10.254" in content

    def test_config_contains_netmask(self, tmp_path):
        """Verify config file contains the netmask."""
        config_path = write_netns_config(
            "ns_ct", "eth1", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            base_dir=str(tmp_path),
        )
        content = config_path.read_text()
        assert "netmask 255.255.255.0" in content

    def test_config_contains_auto_and_iface_directives(self, tmp_path):
        """Verify config has standard interface directives."""
        config_path = write_netns_config(
            "ns_pt", "eth2", "10.0.0.1", "255.255.255.0", "10.0.0.254",
            base_dir=str(tmp_path),
        )
        content = config_path.read_text()
        assert "auto eth2" in content
        assert "iface eth2 inet static" in content

    def test_creates_directories(self, tmp_path):
        """Verify parent directories are created automatically."""
        write_netns_config(
            "ns_mgmt", "eth0", "192.168.1.1", "255.255.255.0", "192.168.1.254",
            base_dir=str(tmp_path),
        )
        assert (tmp_path / "ns_mgmt" / "network").is_dir()

    def test_overwrites_existing_config(self, tmp_path):
        """Verify existing config is overwritten on re-configuration."""
        write_netns_config(
            "ns_ct", "eth1", "192.168.10.1", "255.255.255.0", "192.168.10.254",
            base_dir=str(tmp_path),
        )
        write_netns_config(
            "ns_ct", "eth1", "10.0.0.1", "255.255.255.0", "10.0.0.254",
            base_dir=str(tmp_path),
        )
        content = (tmp_path / "ns_ct" / "network" / "eth1").read_text()
        assert "10.0.0.1/24" in content
        assert "192.168.10.1" not in content


# ---------------------------------------------------------------------------
# Task 3.5: Rollback on failure
# ---------------------------------------------------------------------------


class TestInterfaceServiceRollback:
    """Tests for configuration rollback (Task 3.5)."""

    def test_rollback_restores_previous_config(self):
        """Verify rollback restores previous IP values."""
        from unittest.mock import MagicMock
        from backend.app.services.interface_service import rollback_interface_config

        mock_session = MagicMock()
        mock_interface = MagicMock()
        mock_interface.ipAddress = "10.0.0.1"
        mock_interface.netmask = "255.255.255.0"
        mock_interface.gateway = "10.0.0.254"

        rollback_interface_config(
            mock_session, mock_interface,
            "192.168.1.1", "255.255.0.0", "192.168.1.254",
        )

        assert mock_interface.ipAddress == "192.168.1.1"
        assert mock_interface.netmask == "255.255.0.0"
        assert mock_interface.gateway == "192.168.1.254"
        mock_session.commit.assert_called_once()

    def test_rollback_to_none(self):
        """Verify rollback can restore None (unconfigured) state."""
        from unittest.mock import MagicMock
        from backend.app.services.interface_service import rollback_interface_config

        mock_session = MagicMock()
        mock_interface = MagicMock()

        rollback_interface_config(mock_session, mock_interface, None, None, None)

        assert mock_interface.ipAddress is None
        assert mock_interface.netmask is None
        assert mock_interface.gateway is None


# ---------------------------------------------------------------------------
# Story 5.1, Task 2: Interface statistics query
# ---------------------------------------------------------------------------


class TestGetInterfaceStats:
    """Tests for get_interface_stats (Story 5.1, Task 2)."""

    PROC_NET_DEV_CT = (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
        "    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0\n"
        "  eth1: 1024000    1500    2    0    0     0          0         0  2048000    2000    1    0    0     0       0          0\n"
    )

    PROC_NET_DEV_PT = (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
        "    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0\n"
        "  eth2:  512000     750    0    0    0     0          0         0   768000    1000    0    0    0     0       0          0\n"
    )

    PROC_NET_DEV_MGMT = (
        "Inter-|   Receive                                                |  Transmit\n"
        " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed\n"
        "    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0\n"
        "  eth0:  256000     500    0    0    0     0          0         0   128000     300    0    0    0     0       0          0\n"
    )

    def _make_runner(self, outputs: dict[str, str]):
        """Create a mock runner that returns namespace-specific /proc/net/dev."""
        def mock_runner(*args, **kwargs):
            cmd = args[0]
            # cmd format: ["ip", "netns", "exec", ns_name, "cat", "/proc/net/dev"]
            if len(cmd) >= 4:
                ns_name = cmd[3]
                stdout = outputs.get(ns_name, "")
            else:
                stdout = ""
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

        return mock_runner

    def test_returns_stats_for_all_interfaces(self) -> None:
        """Verify stats returned for CT, PT, MGMT (AC: #2, #7)."""
        runner = self._make_runner({
            "ns_ct": self.PROC_NET_DEV_CT,
            "ns_pt": self.PROC_NET_DEV_PT,
            "ns_mgmt": self.PROC_NET_DEV_MGMT,
        })
        result = get_interface_stats(runner=runner)
        assert "CT" in result
        assert "PT" in result
        assert "MGMT" in result

    def test_ct_stats_parsed_correctly(self) -> None:
        """Verify CT interface stats match /proc/net/dev values (AC: #7)."""
        runner = self._make_runner({
            "ns_ct": self.PROC_NET_DEV_CT,
            "ns_pt": self.PROC_NET_DEV_PT,
            "ns_mgmt": self.PROC_NET_DEV_MGMT,
        })
        result = get_interface_stats(runner=runner)
        ct = result["CT"]
        assert ct["bytesRx"] == 1024000
        assert ct["bytesTx"] == 2048000
        assert ct["packetsRx"] == 1500
        assert ct["packetsTx"] == 2000
        assert ct["errorsRx"] == 2
        assert ct["errorsTx"] == 1

    def test_stats_include_all_required_fields(self) -> None:
        """Verify all required stat fields are present (AC: #7)."""
        runner = self._make_runner({
            "ns_ct": self.PROC_NET_DEV_CT,
            "ns_pt": self.PROC_NET_DEV_PT,
            "ns_mgmt": self.PROC_NET_DEV_MGMT,
        })
        result = get_interface_stats(runner=runner)
        required_fields = {"bytesRx", "bytesTx", "packetsRx", "packetsTx", "errorsRx", "errorsTx"}
        for iface in ("CT", "PT", "MGMT"):
            assert required_fields.issubset(result[iface].keys())

    def test_command_failure_returns_zeros(self) -> None:
        """Verify graceful handling when command fails."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="error")

        result = get_interface_stats(runner=mock_runner)
        for iface in ("CT", "PT", "MGMT"):
            assert result[iface]["bytesRx"] == 0
            assert result[iface]["bytesTx"] == 0

    def test_timeout_returns_zeros(self) -> None:
        """Verify graceful handling on timeout."""
        def mock_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="ip", timeout=5)

        result = get_interface_stats(runner=mock_runner)
        for iface in ("CT", "PT", "MGMT"):
            assert result[iface]["bytesRx"] == 0

    def test_file_not_found_returns_zeros(self) -> None:
        """Verify graceful handling when ip command is not found."""
        def mock_runner(*args, **kwargs):
            raise FileNotFoundError("ip not found")

        result = get_interface_stats(runner=mock_runner)
        for iface in ("CT", "PT", "MGMT"):
            assert result[iface]["bytesRx"] == 0

    def test_queries_correct_namespaces(self) -> None:
        """Verify correct namespaces are queried for each interface."""
        called_namespaces = []

        def mock_runner(*args, **kwargs):
            cmd = args[0]
            if "netns" in cmd:
                called_namespaces.append(cmd[3])
            return subprocess.CompletedProcess(cmd, 0, stdout=self.PROC_NET_DEV_CT, stderr="")

        get_interface_stats(runner=mock_runner)
        assert set(called_namespaces) == {"ns_ct", "ns_pt", "ns_mgmt"}
