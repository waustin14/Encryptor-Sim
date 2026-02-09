"""Unit tests for strongSwan configuration operations (Story 4.2 & 4.3)."""

import os
import subprocess

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.daemon.ops.strongswan_ops import (
    _sanitize_name,
    configure_peer,
    generate_swanctl_config,
    get_tunnel_status,
    initiate_peer,
    reload_peer_config,
    remove_peer_config,
    teardown_peer,
    validate_swanctl_syntax,
    write_routes_config,
)


class TestGenerateSwanctlConfig:
    """Tests for strongSwan config generation."""

    def test_generates_ikev2_config(self) -> None:
        config = generate_swanctl_config(
            name="site-a",
            remote_ip="10.1.1.100",
            psk="my-secret",
            ike_version="ikev2",
        )
        assert "version = 2" in config
        assert "remote_addrs = 10.1.1.100" in config
        assert 'secret = "my-secret"' in config
        assert "site-a" in config

    def test_generates_ikev1_config(self) -> None:
        config = generate_swanctl_config(
            name="site-b",
            remote_ip="10.2.2.200",
            psk="another-secret",
            ike_version="ikev1",
        )
        assert "version = 1" in config

    def test_includes_dpd_params(self) -> None:
        config = generate_swanctl_config(
            name="dpd-peer",
            remote_ip="10.3.3.3",
            psk="psk",
            ike_version="ikev2",
            dpd_action="hold",
            dpd_delay=60,
            dpd_timeout=300,
        )
        assert "dpd_action = hold" in config
        assert "dpd_delay = 60s" in config
        assert "dpd_timeout = 300s" in config

    def test_includes_rekey_time(self) -> None:
        config = generate_swanctl_config(
            name="rekey-peer",
            remote_ip="10.4.4.4",
            psk="psk",
            ike_version="ikev2",
            rekey_time=7200,
        )
        assert "rekey_time = 7200s" in config

    def test_includes_connections_block(self) -> None:
        config = generate_swanctl_config(
            name="test", remote_ip="10.0.0.1", psk="x", ike_version="ikev2"
        )
        assert "connections {" in config

    def test_includes_secrets_block(self) -> None:
        config = generate_swanctl_config(
            name="test", remote_ip="10.0.0.1", psk="x", ike_version="ikev2"
        )
        assert "secrets {" in config

    def test_includes_child_tunnel_mode(self) -> None:
        config = generate_swanctl_config(
            name="test", remote_ip="10.0.0.1", psk="x", ike_version="ikev2"
        )
        assert "mode = tunnel" in config


class TestValidateSwanctlSyntax:
    """Tests for config syntax validation."""

    def test_valid_config_passes(self) -> None:
        config = generate_swanctl_config(
            name="test", remote_ip="10.0.0.1", psk="x", ike_version="ikev2"
        )
        valid, msg = validate_swanctl_syntax(config)
        assert valid is True

    def test_brace_mismatch_fails(self) -> None:
        config = "connections { missing close"
        valid, msg = validate_swanctl_syntax(config)
        assert valid is False
        assert "mismatch" in msg.lower()

    def test_missing_connections_block_fails(self) -> None:
        config = "secrets { }"
        valid, msg = validate_swanctl_syntax(config)
        assert valid is False
        assert "connections" in msg.lower()


class TestConfigurePeer:
    """Tests for the full configure_peer flow."""

    def test_configure_peer_writes_config_file(self, tmp_path) -> None:
        result = configure_peer(
            name="test-peer",
            remote_ip="10.1.1.1",
            psk="secret",
            ike_version="ikev2",
            conf_dir=str(tmp_path),
        )

        assert result["status"] == "success"
        config_file = tmp_path / "test-peer.conf"
        assert config_file.exists()

        content = config_file.read_text()
        assert "remote_addrs = 10.1.1.1" in content
        assert 'secret = "secret"' in content

    def test_configure_peer_returns_config_path(self, tmp_path) -> None:
        result = configure_peer(
            name="path-peer",
            remote_ip="10.2.2.2",
            psk="psk",
            ike_version="ikev2",
            conf_dir=str(tmp_path),
        )

        assert "config_file" in result
        assert "path-peer.conf" in result["config_file"]


class TestInitiatePeer:
    """Tests for tunnel initiation (Story 5.2, Task 1)."""

    def test_initiate_success(self) -> None:
        """Verify successful initiation returns success (AC: #1)."""
        def mock_runner(*args, **kwargs):
            result = subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")
            return result

        result = initiate_peer(name="test-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "initiated" in result["message"].lower()

    def test_initiate_already_established(self) -> None:
        """Verify initiation is idempotent when tunnel already up (AC: #10)."""
        def mock_runner(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args[0], 0, stdout="", stderr="CHILD_SA already INSTALLED"
            )
            return result

        result = initiate_peer(name="existing-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "already" in result["message"].lower()

    def test_initiate_timeout(self) -> None:
        """Verify initiation handles timeout gracefully (AC: #3, Task 1.4)."""
        def mock_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="swanctl", timeout=5)

        result = initiate_peer(name="timeout-peer", runner=mock_runner)
        assert result["status"] == "warning"
        assert "timed out" in result["message"].lower()

    def test_initiate_swanctl_not_found(self) -> None:
        """Verify initiation handles missing swanctl gracefully (AC: #3, Task 1.4)."""
        def mock_runner(*args, **kwargs):
            raise FileNotFoundError("swanctl not found")

        result = initiate_peer(name="nobin-peer", runner=mock_runner)
        assert result["status"] == "warning"
        assert "not available" in result["message"].lower()

    def test_initiate_nonzero_returncode_is_error(self) -> None:
        """Verify non-zero return code yields error status."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(
                args[0], 1, stdout="", stderr="permission denied"
            )

        result = initiate_peer(name="bad-peer", runner=mock_runner)
        assert result["status"] == "error"
        assert "failed" in result["message"].lower()

    def test_initiate_nonzero_already_established_is_success(self) -> None:
        """Verify non-zero return code with already-established message is idempotent."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(
                args[0], 1, stdout="", stderr="CHILD_SA already INSTALLED"
            )

        result = initiate_peer(name="existing-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "already" in result["message"].lower()

    def test_initiate_calls_correct_command(self) -> None:
        """Verify initiation uses correct swanctl command (Task 1.1)."""
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        initiate_peer(name="cmd-peer", runner=mock_runner)
        # Should call load-conns first, then initiate
        assert called_with[0] == ["swanctl", "--load-conns"]
        assert called_with[1] == ["swanctl", "--initiate", "--child", "cmd-peer-child"]


class TestTeardownPeer:
    """Tests for tunnel teardown (Story 4.3, Task 3)."""

    def test_teardown_success(self) -> None:
        """Verify successful teardown returns success."""
        def mock_runner(*args, **kwargs):
            result = subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")
            return result

        result = teardown_peer(name="test-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "torn down" in result["message"].lower()

    def test_teardown_already_down(self) -> None:
        """Verify teardown when tunnel is already down returns success."""
        def mock_runner(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args[0], 1, stdout="", stderr="no matching connection"
            )
            return result

        result = teardown_peer(name="down-peer", runner=mock_runner)
        assert result["status"] == "success"

    def test_teardown_timeout(self) -> None:
        """Verify teardown handles timeout gracefully."""
        def mock_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="swanctl", timeout=5)

        result = teardown_peer(name="timeout-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "timed out" in result["message"].lower()

    def test_teardown_swanctl_not_found(self) -> None:
        """Verify teardown handles missing swanctl gracefully."""
        def mock_runner(*args, **kwargs):
            raise FileNotFoundError("swanctl not found")

        result = teardown_peer(name="nobin-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "not available" in result["message"].lower()


class TestRemovePeerConfig:
    """Tests for config file removal (Story 4.3, Task 4)."""

    def test_remove_existing_config(self, tmp_path) -> None:
        """Verify removing existing config file succeeds."""
        config_file = tmp_path / "test-peer.conf"
        config_file.write_text("connections { }")

        result = remove_peer_config(name="test-peer", conf_dir=str(tmp_path))
        assert result["status"] == "success"
        assert "removed" in result["message"].lower()
        assert not config_file.exists()

    def test_remove_nonexistent_config_idempotent(self, tmp_path) -> None:
        """Verify removing non-existent config file is idempotent."""
        result = remove_peer_config(name="missing-peer", conf_dir=str(tmp_path))
        assert result["status"] == "success"
        assert "already removed" in result["message"].lower()

    def test_remove_config_returns_path_in_message(self, tmp_path) -> None:
        """Verify removal message contains file path."""
        config_file = tmp_path / "path-peer.conf"
        config_file.write_text("connections { }")

        result = remove_peer_config(name="path-peer", conf_dir=str(tmp_path))
        assert "path-peer.conf" in result["message"]

    def test_remove_config_file_permissions_error(self, tmp_path) -> None:
        """Verify removal handles permission errors."""
        config_file = tmp_path / "locked-peer.conf"
        config_file.write_text("data")

        # Make file read-only, and directory read-only too
        config_file.chmod(0o444)
        tmp_path.chmod(0o555)

        result = remove_peer_config(name="locked-peer", conf_dir=str(tmp_path))

        # Restore permissions for cleanup
        tmp_path.chmod(0o755)
        config_file.chmod(0o644)

        assert result["status"] == "error"
        assert "failed" in result["message"].lower()


class TestWriteRoutesConfig:
    """Tests for write_routes_config (Story 4.4, Task 4)."""

    def test_write_routes_updates_local_ts(self, tmp_path) -> None:
        """Verify routes are written as local_ts in config."""
        # Create a peer config file with existing content
        config_content = """# Auto-generated by encryptor-sim daemon
connections {
    site-a {
        version = 2
        remote_addrs = 10.1.1.1
        children {
            site-a-child {
                mode = tunnel
                dpd_action = restart
            }
        }
    }
}
"""
        config_file = tmp_path / "site-a.conf"
        config_file.write_text(config_content)

        routes = [
            {"destination_cidr": "192.168.1.0/24"},
            {"destination_cidr": "10.0.0.0/8"},
        ]

        result = write_routes_config(
            name="site-a", routes=routes, conf_dir=str(tmp_path)
        )

        assert result["status"] == "success"
        content = config_file.read_text()
        assert "local_ts = 192.168.1.0/24,10.0.0.0/8" in content

    def test_write_routes_config_file_not_found(self, tmp_path) -> None:
        """Verify graceful handling when config file doesn't exist."""
        result = write_routes_config(
            name="nonexistent", routes=[], conf_dir=str(tmp_path)
        )
        assert result["status"] == "success"
        assert "not found" in result["message"].lower()

    def test_write_routes_empty_routes_defaults(self, tmp_path) -> None:
        """Verify empty routes uses 0.0.0.0/0 default."""
        config_file = tmp_path / "empty-routes.conf"
        config_file.write_text("connections {\n    test {\n        children {\n            test-child {\n                mode = tunnel\n            }\n        }\n    }\n}\n")

        result = write_routes_config(
            name="empty-routes", routes=[], conf_dir=str(tmp_path)
        )

        assert result["status"] == "success"
        content = config_file.read_text()
        assert "local_ts = 0.0.0.0/0" in content

    def test_write_routes_updates_existing_local_ts(self, tmp_path) -> None:
        """Verify existing local_ts is replaced."""
        config_file = tmp_path / "update-ts.conf"
        config_file.write_text("connections {\n    test {\n        children {\n            test-child {\n                local_ts = 192.168.1.0/24\n            }\n        }\n    }\n}\n")

        routes = [{"destination_cidr": "10.0.0.0/8"}]
        result = write_routes_config(
            name="update-ts", routes=routes, conf_dir=str(tmp_path)
        )

        assert result["status"] == "success"
        content = config_file.read_text()
        assert "local_ts = 10.0.0.0/8" in content
        assert "192.168.1.0/24" not in content


class TestReloadPeerConfig:
    """Tests for reload_peer_config (Story 4.4, Task 4)."""

    def test_reload_success(self) -> None:
        """Verify reload returns success on swanctl success."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        result = reload_peer_config(name="test-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "reloaded" in result["message"].lower()

    def test_reload_swanctl_not_found(self) -> None:
        """Verify reload handles missing swanctl."""
        def mock_runner(*args, **kwargs):
            raise FileNotFoundError("swanctl not found")

        result = reload_peer_config(name="test-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "not available" in result["message"].lower()

    def test_reload_timeout(self) -> None:
        """Verify reload handles timeout."""
        def mock_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="swanctl", timeout=5)

        result = reload_peer_config(name="test-peer", runner=mock_runner)
        assert result["status"] == "success"
        assert "timed out" in result["message"].lower()


class TestGetTunnelStatus:
    """Tests for tunnel status query (Story 5.1, Task 1)."""

    @staticmethod
    def _lookup_peer_ids(names):
        mapping = {
            "site-a": 1,
            "site-b": 2,
            "peer-x": 3,
            "gone-peer": 4,
        }
        return {name: mapping[name] for name in names if name in mapping}

    def test_returns_established_as_up(self) -> None:
        """Verify ESTABLISHED IKE SA maps to 'up' status (AC: #6)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  local  '10.0.0.1' @ 10.0.0.1[500]\n"
            "  remote '10.1.1.100' @ 10.1.1.100[500]\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result[1] == "up"

    def test_returns_connecting_as_negotiating(self) -> None:
        """Verify CONNECTING IKE SA maps to 'negotiating' (AC: #6)."""
        output = (
            "site-b: #2, CONNECTING, IKEv2, "
            "00000000_i 00000000_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result[2] == "negotiating"

    def test_returns_rekeying_as_negotiating(self) -> None:
        """Verify REKEYING IKE SA maps to 'negotiating' (AC: #6)."""
        output = (
            "peer-x: #3, REKEYING, IKEv2, "
            "aabbccdd_i eeffaabb_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result[3] == "negotiating"

    def test_returns_deleting_as_down(self) -> None:
        """Verify DELETING IKE SA maps to 'down' (AC: #6)."""
        output = (
            "gone-peer: #4, DELETING, IKEv2, "
            "11223344_i 55667788_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result[4] == "down"

    def test_multiple_peers(self) -> None:
        """Verify multiple peers are parsed correctly (AC: #1)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  local  '10.0.0.1' @ 10.0.0.1[500]\n"
            "  remote '10.1.1.100' @ 10.1.1.100[500]\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "site-b: #2, CONNECTING, IKEv2, "
            "00000000_i 00000000_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result[1] == "up"
        assert result[2] == "negotiating"

    def test_empty_output_returns_empty_dict(self) -> None:
        """Verify empty swanctl output returns empty dict."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result == {}

    def test_swanctl_not_found_returns_empty_dict(self) -> None:
        """Verify graceful handling when swanctl is not available."""
        def mock_runner(*args, **kwargs):
            raise FileNotFoundError("swanctl not found")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result == {}

    def test_swanctl_timeout_returns_empty_dict(self) -> None:
        """Verify graceful handling on timeout."""
        def mock_runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="swanctl", timeout=5)

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result == {}

    def test_swanctl_nonzero_exit_returns_empty_dict(self) -> None:
        """Verify graceful handling on command failure."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="error")

        result = get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert result == {}

    def test_calls_swanctl_list_sas(self) -> None:
        """Verify the correct swanctl command is called."""
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        get_tunnel_status(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )
        assert called_with[0] == ["swanctl", "--list-sas"]


class TestGetTunnelTelemetry:
    """Tests for tunnel telemetry extraction (Story 5.4, Task 1)."""

    @staticmethod
    def _lookup_peer_ids(names):
        mapping = {
            "site-a": 1,
            "site-b": 2,
            "peer-x": 3,
        }
        return {name: mapping[name] for name in names if name in mapping}

    def test_returns_telemetry_structure_with_status(self) -> None:
        """Verify telemetry includes status field (AC: #1)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  established: 3600 seconds ago\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "    bytes_in:  1024, bytes_out:  2048\n"
            "    packets_in:  10, packets_out:  20\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert 1 in result
        assert result[1]["status"] == "up"

    def test_returns_established_seconds(self) -> None:
        """Verify telemetry includes establishedSec field (AC: #2)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  established: 3600 seconds ago\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "    bytes_in:  1024, bytes_out:  2048\n"
            "    packets_in:  10, packets_out:  20\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert result[1]["establishedSec"] == 3600

    def test_returns_traffic_counters(self) -> None:
        """Verify telemetry includes bytes and packets counters (AC: #3)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  established: 100 seconds ago\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "    bytes_in:  4096, bytes_out:  8192\n"
            "    packets_in:  32, packets_out:  64\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert result[1]["bytesIn"] == 4096
        assert result[1]["bytesOut"] == 8192
        assert result[1]["packetsIn"] == 32
        assert result[1]["packetsOut"] == 64

    def test_defaults_safely_when_telemetry_missing(self) -> None:
        """Verify telemetry defaults to safe values when fields missing (AC: #8, #3)."""
        output = (
            "site-b: #2, ESTABLISHED, IKEv2, "
            "00000000_i 00000000_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert result[2]["status"] == "up"
        assert result[2]["establishedSec"] == 0
        assert result[2]["bytesIn"] == 0
        assert result[2]["bytesOut"] == 0
        assert result[2]["packetsIn"] == 0
        assert result[2]["packetsOut"] == 0

    def test_negotiating_tunnel_has_zero_telemetry(self) -> None:
        """Verify negotiating tunnels have zero telemetry values (AC: #3, #8)."""
        output = (
            "peer-x: #3, CONNECTING, IKEv2, "
            "00000000_i 00000000_r\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert result[3]["status"] == "negotiating"
        assert result[3]["establishedSec"] == 0
        assert result[3]["bytesIn"] == 0

    def test_multiple_peers_with_varying_telemetry(self) -> None:
        """Verify parser handles multiple peers with different telemetry states (AC: #10)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  established: 7200 seconds ago\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "    bytes_in:  10240, bytes_out:  20480\n"
            "    packets_in:  100, packets_out:  200\n"
            "site-b: #2, CONNECTING, IKEv2, "
            "11223344_i 55667788_r\n"
            "peer-x: #3, ESTABLISHED, IKEv2, "
            "aabbccdd_i eeffaabb_r\n"
            "  established: 300 seconds ago\n"
            "  peer-x-child: #3, INSTALLED, TUNNEL\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        # site-a has full telemetry
        assert result[1]["status"] == "up"
        assert result[1]["establishedSec"] == 7200
        assert result[1]["bytesIn"] == 10240

        # site-b is negotiating with zero telemetry
        assert result[2]["status"] == "negotiating"
        assert result[2]["establishedSec"] == 0

        # peer-x has partial telemetry (established but no counters)
        assert result[3]["status"] == "up"
        assert result[3]["establishedSec"] == 300
        assert result[3]["bytesIn"] == 0

    def test_swanctl_failure_returns_empty_dict(self) -> None:
        """Verify graceful degradation when swanctl fails (AC: #8)."""
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="error")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        assert result == {}

    def test_malformed_output_extracts_what_it_can(self) -> None:
        """Verify parser extracts available data from malformed output (AC: #8, #10)."""
        output = (
            "site-a: #1, ESTABLISHED, IKEv2, "
            "abcdef01_i 12345678_r\n"
            "  site-a-child: #1, INSTALLED, TUNNEL\n"
            "    bytes_in:  invalid, bytes_out:  2048\n"
        )

        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout=output, stderr="")

        from backend.daemon.ops.strongswan_ops import get_tunnel_telemetry
        result = get_tunnel_telemetry(
            runner=mock_runner,
            peer_id_lookup=self._lookup_peer_ids,
        )

        # Should still extract status and default invalid fields
        assert result[1]["status"] == "up"
        assert result[1]["bytesIn"] == 0  # Invalid value defaults to 0
        assert result[1]["bytesOut"] == 2048  # Valid value parsed


class TestSanitizeName:
    """Tests for peer name sanitization for strongSwan identifiers."""

    def test_no_change_for_simple_name(self) -> None:
        assert _sanitize_name("site-a") == "site-a"

    def test_spaces_replaced_with_underscores(self) -> None:
        assert _sanitize_name("Site A") == "Site_A"

    def test_multiple_spaces(self) -> None:
        assert _sanitize_name("My Remote Site") == "My_Remote_Site"

    def test_special_characters_replaced(self) -> None:
        assert _sanitize_name("peer@office#1") == "peer_office_1"

    def test_hyphens_and_underscores_preserved(self) -> None:
        assert _sanitize_name("my-peer_name") == "my-peer_name"


class TestSpacesInPeerName:
    """Tests verifying that peer names with spaces work correctly."""

    def test_config_uses_sanitized_identifiers(self) -> None:
        """Verify config identifiers don't contain spaces."""
        config = generate_swanctl_config(
            name="Site A",
            remote_ip="10.1.1.100",
            psk="secret",
            ike_version="ikev2",
        )
        assert "Site_A {" in config
        assert "Site_A-child {" in config
        assert "ike-Site_A {" in config
        # Original name preserved in comment
        assert "# Peer: Site A" in config

    def test_initiate_uses_sanitized_child_name(self) -> None:
        """Verify initiation command uses sanitized CHILD_SA name."""
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        initiate_peer(name="Site A", runner=mock_runner)
        assert called_with[1] == ["swanctl", "--initiate", "--child", "Site_A-child"]

    def test_teardown_uses_sanitized_child_name(self) -> None:
        """Verify teardown command uses sanitized CHILD_SA name."""
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        teardown_peer(name="Site A", runner=mock_runner)
        assert called_with[0] == ["swanctl", "--terminate", "--child", "Site_A-child"]

    def test_configure_peer_writes_sanitized_filename(self, tmp_path) -> None:
        """Verify config file uses sanitized name."""
        result = configure_peer(
            name="Site A",
            remote_ip="10.1.1.1",
            psk="secret",
            ike_version="ikev2",
            conf_dir=str(tmp_path),
        )
        assert result["status"] == "success"
        assert (tmp_path / "Site_A.conf").exists()
        assert not (tmp_path / "Site A.conf").exists()

    def test_remove_peer_config_uses_sanitized_filename(self, tmp_path) -> None:
        """Verify config removal uses sanitized filename."""
        config_file = tmp_path / "Site_A.conf"
        config_file.write_text("connections { }")

        result = remove_peer_config(name="Site A", conf_dir=str(tmp_path))
        assert result["status"] == "success"
        assert not config_file.exists()
