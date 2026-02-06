"""Background polling tasks for tunnel status and interface statistics.

Polls the daemon at regular intervals and broadcasts changes to
connected WebSocket clients.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.services.daemon_ipc import send_command
from backend.app.ws.monitoring import get_monitoring_ws_manager
from backend.app.config import get_settings
from backend.app.db.session import create_session_factory
from backend.app.models.peer import Peer

logger = logging.getLogger(__name__)

TUNNEL_POLL_INTERVAL = 0.5  # seconds (NFR7 < 1s)
INTERFACE_POLL_INTERVAL = 2  # seconds (NFR6 1-2s)

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


async def poll_tunnel_status() -> None:
    """Poll daemon for tunnel telemetry and emit changes.

    Detects tunnel state changes and traffic flow using byte/packet
    counter deltas. Broadcasts tunnel.status_changed events with
    telemetry fields when status or traffic flow state changes.
    """
    previous_telemetry: dict[int, dict] = {}
    previous_traffic_state: dict[int, bool] = {}
    last_traffic_at: dict[int, str] = {}

    while True:
        try:
            raw_telemetry: dict[str, dict] = {}
            raw_status: dict[str, str] = {}

            try:
                response = send_command("get_tunnel_telemetry")
                candidate = response.get("result", {})
                if isinstance(candidate, dict):
                    raw_telemetry = candidate
            except Exception as e:
                logger.warning(f"Telemetry polling failed, trying status fallback: {e}")

            if not raw_telemetry:
                try:
                    status_response = send_command("get_tunnel_status")
                    candidate = status_response.get("result", {})
                    if isinstance(candidate, dict):
                        raw_status = candidate
                except Exception as e:
                    logger.warning(f"Status fallback polling failed: {e}")

            current_telemetry: dict[int, dict] = {}
            status_fallback: dict[int, str] = {}

            # Coerce string keys to int peer IDs
            for key, value in raw_telemetry.items():
                try:
                    peer_id = int(key)
                except (TypeError, ValueError):
                    continue
                current_telemetry[peer_id] = value

            for key, value in raw_status.items():
                try:
                    peer_id = int(key)
                except (TypeError, ValueError):
                    continue
                status_fallback[peer_id] = value

            peers = _load_peers()
            peer_map = {peer.peerId: peer.name for peer in peers}

            manager = get_monitoring_ws_manager()
            now = datetime.now(timezone.utc).isoformat()

            # Detect changes and compute traffic deltas
            for peer_id, peer_name in peer_map.items():
                fallback_status = status_fallback.get(peer_id, "down")
                current = current_telemetry.get(peer_id, {
                    "status": fallback_status,
                    "establishedSec": 0,
                    "bytesIn": 0,
                    "bytesOut": 0,
                    "packetsIn": 0,
                    "packetsOut": 0,
                })
                previous = previous_telemetry.get(peer_id)

                # Compute traffic delta (AC: #4)
                is_passing_traffic = False
                if previous:
                    bytes_delta = (
                        current.get("bytesIn", 0) - previous.get("bytesIn", 0) +
                        current.get("bytesOut", 0) - previous.get("bytesOut", 0)
                    )
                    packets_delta = (
                        current.get("packetsIn", 0) - previous.get("packetsIn", 0) +
                        current.get("packetsOut", 0) - previous.get("packetsOut", 0)
                    )
                    is_passing_traffic = (bytes_delta > 0) or (packets_delta > 0)

                    # Update last traffic timestamp (AC: #4, Task 2.3)
                    if is_passing_traffic:
                        last_traffic_at[peer_id] = now

                # Determine if event should be emitted
                # Emit if status changed OR traffic flow state changed OR first poll
                status_changed = (
                    not previous or
                    current.get("status") != previous.get("status")
                )
                traffic_state_changed = (
                    previous is not None and
                    is_passing_traffic != previous_traffic_state.get(peer_id, False)
                )

                if status_changed or traffic_state_changed:
                    event: dict[str, Any] = {
                        "type": "tunnel.status_changed",
                        "data": {
                            "peerId": peer_id,
                            "peerName": peer_name,
                            "status": current.get("status", "down"),
                            "establishedSec": current.get("establishedSec", 0),
                            "bytesIn": current.get("bytesIn", 0),
                            "bytesOut": current.get("bytesOut", 0),
                            "packetsIn": current.get("packetsIn", 0),
                            "packetsOut": current.get("packetsOut", 0),
                            "isPassingTraffic": is_passing_traffic,
                            "lastTrafficAt": last_traffic_at.get(peer_id),
                            "timestamp": now,
                        },
                    }
                    await manager.broadcast(event)

                # Track current traffic state for next iteration
                previous_traffic_state[peer_id] = is_passing_traffic

            previous_telemetry = current_telemetry.copy()

        except Exception as e:
            logger.error(f"Error polling tunnel status: {e}")

        await asyncio.sleep(TUNNEL_POLL_INTERVAL)


async def poll_interface_stats() -> None:
    """Poll daemon for interface statistics and broadcast updates.

    Emits interface.stats_updated events for each interface
    at every poll interval.
    """
    while True:
        try:
            response = send_command("get_interface_stats")
            stats: dict[str, dict[str, int]] = response.get("result", {})

            manager = get_monitoring_ws_manager()
            timestamp = datetime.now(timezone.utc).isoformat()

            for interface_name, interface_stats in stats.items():
                event: dict[str, Any] = {
                    "type": "interface.stats_updated",
                    "data": {
                        "interface": interface_name,
                        **interface_stats,
                        "timestamp": timestamp,
                    },
                }
                await manager.broadcast(event)

        except Exception as e:
            logger.error(f"Error polling interface stats: {e}")

        await asyncio.sleep(INTERFACE_POLL_INTERVAL)
