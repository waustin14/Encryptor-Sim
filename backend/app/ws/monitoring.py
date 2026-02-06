"""WebSocket endpoint for real-time tunnel and interface monitoring.

Provides authenticated WebSocket at /api/v1/ws for receiving
tunnel.status_changed and interface.stats_updated events.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.app.config import get_settings
from backend.app.db.session import create_session_factory
from backend.app.models.peer import Peer
from backend.app.services.daemon_ipc import send_command

from backend.app.auth.jwt import verify_token
from backend.app.ws.manager import WebSocketManager

router = APIRouter()

_manager = WebSocketManager()
_session_factory = None


def _get_session():
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_settings().database_url)
    return _session_factory()


def _load_peers() -> list[Peer]:
    session = _get_session()
    try:
        return session.query(Peer).all()
    finally:
        session.close()


def _coerce_peer_status(raw_status: dict[str, str]) -> dict[int, str]:
    statuses: dict[int, str] = {}
    for key, value in raw_status.items():
        try:
            peer_id = int(key)
        except (TypeError, ValueError):
            continue
        statuses[peer_id] = value
    return statuses


def _coerce_peer_telemetry(raw_telemetry: dict[str, dict]) -> dict[int, dict]:
    """Coerce string peer IDs to integers in telemetry dict."""
    telemetry: dict[int, dict] = {}
    for key, value in raw_telemetry.items():
        try:
            peer_id = int(key)
        except (TypeError, ValueError):
            continue
        telemetry[peer_id] = value
    return telemetry


def get_monitoring_ws_manager() -> WebSocketManager:
    """Return the monitoring WebSocket manager singleton."""
    return _manager


@router.websocket("/api/v1/ws")
async def monitoring_websocket(
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    """WebSocket endpoint for real-time tunnel and interface updates.

    Auth: JWT access token via query parameter ?token=<jwt>
    Events emitted:
    - tunnel.status_changed: { type, data: { peerId, peerName, status, timestamp } }
    - interface.stats_updated: { type, data: { interface, stats..., timestamp } }
    """
    if not token:
        await websocket.close(code=1008)
        return

    user_id = verify_token(token, expected_type="access")
    if user_id is None:
        await websocket.close(code=1008)
        return

    await _manager.connect(websocket)
    try:
        peers = _load_peers()
        peer_map = {peer.peerId: peer.name for peer in peers}
        raw_telemetry: dict[str, dict] = {}
        raw_status: dict[str, str] = {}

        try:
            telemetry_response = send_command("get_tunnel_telemetry")
            candidate = telemetry_response.get("result", {})
            if isinstance(candidate, dict):
                raw_telemetry = candidate
        except Exception:
            raw_telemetry = {}

        if not raw_telemetry:
            try:
                status_response = send_command("get_tunnel_status")
                candidate = status_response.get("result", {})
                if isinstance(candidate, dict):
                    raw_status = candidate
            except Exception:
                raw_status = {}

        telemetry_by_id = _coerce_peer_telemetry(raw_telemetry)
        status_by_id = _coerce_peer_status(raw_status)

        for peer_id, peer_name in peer_map.items():
            fallback_status = status_by_id.get(peer_id, "down")
            telemetry = telemetry_by_id.get(peer_id, {
                "status": fallback_status,
                "establishedSec": 0,
                "bytesIn": 0,
                "bytesOut": 0,
                "packetsIn": 0,
                "packetsOut": 0,
            })
            await websocket.send_json(
                {
                    "type": "tunnel.status_changed",
                    "data": {
                        "peerId": peer_id,
                        "peerName": peer_name,
                        "status": telemetry.get("status", "down"),
                        "establishedSec": telemetry.get("establishedSec", 0),
                        "bytesIn": telemetry.get("bytesIn", 0),
                        "bytesOut": telemetry.get("bytesOut", 0),
                        "packetsIn": telemetry.get("packetsIn", 0),
                        "packetsOut": telemetry.get("packetsOut", 0),
                        "isPassingTraffic": False,  # No previous data on connect
                        "lastTrafficAt": None,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
            )

        stats = send_command("get_interface_stats").get("result", {})
        timestamp = datetime.now(timezone.utc).isoformat()
        for interface_name, interface_stats in stats.items():
            await websocket.send_json(
                {
                    "type": "interface.stats_updated",
                    "data": {
                        "interface": interface_name,
                        **interface_stats,
                        "timestamp": timestamp,
                    },
                }
            )
    except Exception:
        # Best-effort initial snapshot; streaming updates will continue.
        pass
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _manager.disconnect(websocket)
