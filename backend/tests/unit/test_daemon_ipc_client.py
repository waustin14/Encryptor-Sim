import json
import socket
import tempfile
import threading
from pathlib import Path

import pytest

from backend.app.services.daemon_ipc import send_command


def test_send_command_round_trip() -> None:
    with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
        socket_path = str(Path(tmpdir) / "daemon.sock")
        received: dict[str, object] = {}
        ready = threading.Event()

        def run_server() -> None:
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.bind(socket_path)
                    server.listen(1)
                    ready.set()
                    connection, _ = server.accept()
                    with connection:
                        raw = connection.recv(4096)
                        request = json.loads(raw.split(b"\n", 1)[0].decode("utf-8"))
                        received.update(request)
                        response = {"status": "ok", "result": {"status": "ok"}}
                        connection.sendall(json.dumps(response).encode("utf-8") + b"\n")
            except PermissionError:
                ready.set()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        ready.wait(timeout=1)

        if not Path(socket_path).exists():
            pytest.skip("unix socket bind not permitted in this environment")

        response = send_command(
            "enforce_isolation",
            {"namespaces": ["ns_pt", "ns_ct"]},
            socket_path=socket_path,
        )

        thread.join(timeout=1)
        assert received["command"] == "enforce_isolation"
        assert received["payload"] == {"namespaces": ["ns_pt", "ns_ct"]}
        assert response["result"] == {"status": "ok"}
