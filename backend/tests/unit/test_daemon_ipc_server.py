import os
import socket
from pathlib import Path
from unittest.mock import MagicMock

from backend.daemon.ipc.server import _restrict_socket_permissions, handle_request


def test_restrict_socket_permissions(tmp_path: Path) -> None:
    socket_path = tmp_path / "daemon.sock"
    socket_path.touch()
    _restrict_socket_permissions(socket_path)

    mode = os.stat(socket_path).st_mode & 0o777
    assert mode == 0o600
    if os.geteuid() == 0:
        stat = os.stat(socket_path)
        assert stat.st_uid == 0
        assert stat.st_gid == 0


def test_handle_request_broken_pipe_on_response_does_not_raise() -> None:
    """Verify BrokenPipeError when sending response doesn't crash the daemon."""
    conn = MagicMock(spec=socket.socket)
    conn.recv.return_value = b'{"command": "ping", "payload": {}}\n'
    conn.sendall.side_effect = BrokenPipeError("client gone")

    def handler(cmd, payload):
        return {"status": "ok"}

    # Should not raise - the BrokenPipeError should be caught and logged
    handle_request(conn, handler)


def test_handle_request_broken_pipe_on_error_response_does_not_raise() -> None:
    """Verify BrokenPipeError when sending error response doesn't crash the daemon."""
    conn = MagicMock(spec=socket.socket)
    conn.recv.return_value = b'{"command": "boom", "payload": {}}\n'
    conn.sendall.side_effect = BrokenPipeError("client gone")

    def handler(cmd, payload):
        raise RuntimeError("command failed")

    # Should not raise - both the RuntimeError and BrokenPipeError should be caught
    handle_request(conn, handler)
