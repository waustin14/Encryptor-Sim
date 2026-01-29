from __future__ import annotations

import json
import socket
from typing import Any

from backend.app.config import get_settings


def send_command(
    command: str,
    payload: dict[str, Any] | None = None,
    *,
    socket_path: str | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    resolved_path = socket_path or get_settings().daemon_socket_path
    request = {"command": command, "payload": payload or {}}
    data = json.dumps(request).encode("utf-8") + b"\n"

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(resolved_path)
        client.sendall(data)

        buffer = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            buffer += chunk
            if b"\n" in buffer:
                break
        response = buffer.split(b"\n", 1)[0]

    if not response:
        raise RuntimeError("Daemon IPC returned empty response")

    payload = json.loads(response.decode("utf-8"))
    if payload.get("status") != "ok":
        raise RuntimeError(payload.get("error", "Daemon IPC error"))
    return payload
