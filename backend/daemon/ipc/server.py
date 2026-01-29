from __future__ import annotations

import json
import logging
import os
import signal
import socket
from pathlib import Path
from typing import Any, Callable

from backend.daemon.ipc.commands import handle_command

logger = logging.getLogger(__name__)
_shutdown_requested = False


def _signal_handler(signum: int, frame: Any) -> None:
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    _shutdown_requested = True


def _read_message(connection: socket.socket) -> str:
    buffer = b""
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        buffer += chunk
        if b"\n" in buffer:
            break
    return buffer.split(b"\n", 1)[0].decode("utf-8")


def _write_message(connection: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8") + b"\n"
    connection.sendall(data)


def _restrict_socket_permissions(path: Path) -> None:
    os.chmod(path, 0o600)
    if os.geteuid() == 0:
        os.chown(path, 0, 0)


def handle_request(
    connection: socket.socket,
    handler: Callable[[str, dict[str, Any] | None], dict[str, str]] = handle_command,
) -> None:
    try:
        message = _read_message(connection)
        request = json.loads(message) if message else {}
        command = request.get("command")
        payload = request.get("payload")
        if not command:
            raise ValueError("Missing command")
        result = handler(command, payload)
        _write_message(connection, {"status": "ok", "result": result})
    except Exception as exc:
        logger.exception(f"Error handling IPC request: {exc}")
        _write_message(connection, {"status": "error", "error": str(exc)})


def serve(
    socket_path: str,
    handler: Callable[[str, dict[str, Any] | None], dict[str, str]] = handle_command,
    connection_timeout: float = 5.0,
) -> None:
    global _shutdown_requested
    path = Path(socket_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(socket_path)
        _restrict_socket_permissions(path)
        server.listen(1)
        server.settimeout(1.0)
        logger.info(f"Daemon IPC server listening on {socket_path}")
        while not _shutdown_requested:
            try:
                connection, _ = server.accept()
                connection.settimeout(connection_timeout)
                with connection:
                    handle_request(connection, handler)
            except socket.timeout:
                continue
        logger.info("Daemon IPC server shutdown complete")
