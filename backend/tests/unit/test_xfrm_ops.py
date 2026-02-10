"""Unit tests for XFRM interface operations."""

import os
import subprocess

os.environ.setdefault("APP_PSK_ENCRYPTION_KEY", "test-key-for-testing-32bytes1")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-jwt-testing")

from backend.daemon.ops.xfrm_ops import (
    _if_id_from_peer_id,
    _xfrm_dev_name,
    add_pt_return_route,
    add_tunnel_route,
    create_xfrm_interface,
    delete_xfrm_interface,
    remove_pt_return_route,
    remove_tunnel_routes,
)


class TestHelpers:
    """Tests for helper functions."""

    def test_if_id_from_peer_id_is_identity(self) -> None:
        assert _if_id_from_peer_id(1) == 1
        assert _if_id_from_peer_id(42) == 42

    def test_xfrm_dev_name(self) -> None:
        assert _xfrm_dev_name(1) == "xfrm1"
        assert _xfrm_dev_name(99) == "xfrm99"


class TestCreateXfrmInterface:
    """Tests for XFRM interface creation."""

    def test_creates_interface_with_correct_commands(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        result = create_xfrm_interface(1, 1, runner=mock_runner)

        assert result == "xfrm1"
        # First call: delete existing (idempotent cleanup)
        assert called_with[0] == ["ip", "link", "del", "xfrm1"]
        # Second call: create xfrmi inside ns_ct linked to eth1
        assert called_with[1] == [
            "ip", "netns", "exec", "ns_ct",
            "ip", "link", "add", "xfrm1",
            "type", "xfrm",
            "dev", "eth1",
            "if_id", "1",
        ]
        # Third call: move xfrmi from ns_ct to default namespace (PID 1)
        assert called_with[2] == [
            "ip", "netns", "exec", "ns_ct",
            "ip", "link", "set", "xfrm1", "netns", "1",
        ]
        # Fourth call: set MTU
        assert called_with[3] == ["ip", "link", "set", "xfrm1", "mtu", "1400"]
        # Fifth call: bring up
        assert called_with[4] == ["ip", "link", "set", "xfrm1", "up"]

    def test_uses_peer_id_for_naming(self) -> None:
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        result = create_xfrm_interface(42, 42, runner=mock_runner)
        assert result == "xfrm42"

    def test_raises_on_create_failure(self) -> None:
        call_count = [0]

        def mock_runner(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # The create command
                raise subprocess.CalledProcessError(1, "ip")
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        try:
            create_xfrm_interface(1, 1, runner=mock_runner)
            assert False, "Should have raised"
        except subprocess.CalledProcessError:
            pass


class TestDeleteXfrmInterface:
    """Tests for XFRM interface deletion."""

    def test_deletes_interface(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        delete_xfrm_interface(1, runner=mock_runner)
        assert called_with[0] == ["ip", "link", "del", "xfrm1"]

    def test_idempotent_when_not_found(self) -> None:
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="not found")

        # Should not raise
        delete_xfrm_interface(99, runner=mock_runner)


class TestAddTunnelRoute:
    """Tests for tunnel route management."""

    def test_adds_route_with_correct_command(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        add_tunnel_route(1, "192.168.1.0/24", runner=mock_runner)
        assert called_with[0] == [
            "ip", "route", "replace", "192.168.1.0/24", "dev", "xfrm1",
        ]


class TestRemoveTunnelRoutes:
    """Tests for tunnel route removal."""

    def test_removes_routes_for_device(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            if args[0][:3] == ["ip", "route", "show"]:
                return subprocess.CompletedProcess(
                    args[0], 0,
                    stdout="192.168.1.0/24 dev xfrm1\n10.0.0.0/8 dev xfrm1\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        remove_tunnel_routes(1, runner=mock_runner)
        # Should have called show, then two deletes
        assert len(called_with) == 3
        assert called_with[1] == ["ip", "route", "del", "192.168.1.0/24", "dev", "xfrm1"]
        assert called_with[2] == ["ip", "route", "del", "10.0.0.0/8", "dev", "xfrm1"]

    def test_no_op_when_no_routes(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        remove_tunnel_routes(1, runner=mock_runner)
        # Only the show command
        assert len(called_with) == 1


class TestPtReturnRoutes:
    """Tests for ns_pt return route management."""

    def test_add_pt_return_route(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        add_pt_return_route("192.168.1.0/24", runner=mock_runner)
        assert called_with[0] == [
            "ip", "netns", "exec", "ns_pt",
            "ip", "route", "replace", "192.168.1.0/24", "via", "169.254.0.1",
        ]

    def test_remove_pt_return_route(self) -> None:
        called_with = []

        def mock_runner(*args, **kwargs):
            called_with.append(args[0])
            return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

        remove_pt_return_route("192.168.1.0/24", runner=mock_runner)
        assert called_with[0] == [
            "ip", "netns", "exec", "ns_pt",
            "ip", "route", "del", "192.168.1.0/24", "via", "169.254.0.1",
        ]

    def test_remove_pt_return_route_idempotent(self) -> None:
        def mock_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 2, stdout="", stderr="not found")

        # Should not raise
        remove_pt_return_route("10.0.0.0/8", runner=mock_runner)
