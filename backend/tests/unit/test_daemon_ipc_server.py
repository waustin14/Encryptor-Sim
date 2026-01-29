import os
from pathlib import Path

from backend.daemon.ipc.server import _restrict_socket_permissions


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
