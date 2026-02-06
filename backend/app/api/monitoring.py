"""Monitoring REST API endpoints for automation consumers.

Provides authenticated REST access to tunnel telemetry and interface
statistics using daemon IPC with graceful fallback behavior.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_session
from backend.app.models.peer import Peer
from backend.app.models.user import User
from backend.app.schemas.monitoring import (
    InterfaceStatsEntry,
    InterfaceStatsEnvelope,
    TunnelTelemetryEntry,
    TunnelTelemetryEnvelope,
)
from backend.app.services.daemon_ipc import send_command

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/tunnels", response_model=TunnelTelemetryEnvelope)
def get_tunnel_telemetry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TunnelTelemetryEnvelope:
    """Get tunnel telemetry for all configured peers.

    Uses daemon IPC get_tunnel_telemetry with fallback to get_tunnel_status
    when telemetry is unavailable.
    """
    peers = db.query(Peer).all()
    peer_map = {peer.peerId: peer.name for peer in peers}

    raw_telemetry: dict = {}
    raw_status: dict = {}
    daemon_available = True
    used_fallback = False

    # Try full telemetry first
    try:
        response = send_command("get_tunnel_telemetry")
        candidate = response.get("result", {})
        if isinstance(candidate, dict):
            raw_telemetry = candidate
    except Exception as e:
        logger.warning("Telemetry query failed, trying status fallback: %s", e)

    # Fall back to status-only if telemetry empty
    if not raw_telemetry:
        try:
            status_response = send_command("get_tunnel_status")
            candidate = status_response.get("result", {})
            if isinstance(candidate, dict):
                raw_status = candidate
                used_fallback = True
        except Exception as e:
            daemon_available = False
            logger.warning("Status fallback also failed: %s", e)

    timestamp = datetime.now(timezone.utc).isoformat()
    entries: list[TunnelTelemetryEntry] = []

    for peer_id, peer_name in peer_map.items():
        # Daemon returns string keys; try both int and str
        telemetry = raw_telemetry.get(peer_id) or raw_telemetry.get(str(peer_id))
        fallback = raw_status.get(peer_id) or raw_status.get(str(peer_id))

        if telemetry and isinstance(telemetry, dict):
            entries.append(TunnelTelemetryEntry(
                peerId=peer_id,
                peerName=peer_name,
                status=telemetry.get("status", "down"),
                establishedSec=telemetry.get("establishedSec", 0),
                bytesIn=telemetry.get("bytesIn", 0),
                bytesOut=telemetry.get("bytesOut", 0),
                packetsIn=telemetry.get("packetsIn", 0),
                packetsOut=telemetry.get("packetsOut", 0),
                isPassingTraffic=telemetry.get("isPassingTraffic"),
                lastTrafficAt=telemetry.get("lastTrafficAt"),
                timestamp=timestamp,
            ))
        elif fallback:
            status_val = fallback if isinstance(fallback, str) else "down"
            entries.append(TunnelTelemetryEntry(
                peerId=peer_id,
                peerName=peer_name,
                status=status_val,
                timestamp=timestamp,
            ))
        else:
            entries.append(TunnelTelemetryEntry(
                peerId=peer_id,
                peerName=peer_name,
                status="down",
                timestamp=timestamp,
            ))

    meta: dict = {
        "count": len(entries),
        "daemonAvailable": daemon_available,
    }
    if used_fallback:
        meta["warning"] = (
            "Telemetry unavailable; using status fallback (counters unavailable)"
        )
    elif not daemon_available:
        meta["warning"] = (
            "Daemon unavailable; showing default status for all peers"
        )

    return TunnelTelemetryEnvelope(data=entries, meta=meta)


@router.get("/interfaces", response_model=InterfaceStatsEnvelope)
def get_interface_statistics(
    current_user: User = Depends(get_current_user),
) -> InterfaceStatsEnvelope:
    """Get interface statistics for CT, PT, and MGMT interfaces.

    Uses daemon IPC get_interface_stats.
    """
    daemon_available = True
    stats: dict = {}

    try:
        response = send_command("get_interface_stats")
        stats = response.get("result", {})
    except Exception as e:
        daemon_available = False
        logger.warning("Interface stats query failed: %s", e)

    timestamp = datetime.now(timezone.utc).isoformat()
    entries: list[InterfaceStatsEntry] = []

    for interface_name, interface_stats in stats.items():
        entries.append(InterfaceStatsEntry(
            interface=interface_name,
            bytesRx=interface_stats.get("bytesRx", 0),
            bytesTx=interface_stats.get("bytesTx", 0),
            packetsRx=interface_stats.get("packetsRx", 0),
            packetsTx=interface_stats.get("packetsTx", 0),
            errorsRx=interface_stats.get("errorsRx", 0),
            errorsTx=interface_stats.get("errorsTx", 0),
            timestamp=timestamp,
        ))

    meta: dict = {
        "count": len(entries),
        "daemonAvailable": daemon_available,
    }
    if not daemon_available:
        meta["warning"] = "Daemon unavailable; no interface statistics available"

    return InterfaceStatsEnvelope(data=entries, meta=meta)
