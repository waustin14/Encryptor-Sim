"""IPsec peer configuration API endpoints.

Provides endpoints for creating, listing, viewing, updating, and deleting
IPsec peer configurations.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_session
from backend.app.models.peer import Peer
from backend.app.models.user import User
from backend.app.schemas.ipsec_peer import (
    PeerCreateRequest,
    PeerEnvelope,
    PeerListEnvelope,
    PeerResponse,
    PeerUpdateRequest,
)
from backend.app.services.daemon_ipc import send_command
from backend.app.services.ipsec_peer_service import (
    create_peer,
    delete_peer,
    get_all_peers,
    get_decrypted_psk,
    get_peer_by_id,
    get_peer_by_name,
    update_peer,
    validate_peer_config,
)
from backend.app.services.route_service import get_routes_for_peer
from backend.app.utils.rfc7807 import create_rfc7807_error
from backend.app.ws.monitoring import get_monitoring_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/peers", tags=["peers"])


def _build_validation_params_for_update(
    request: PeerUpdateRequest, peer: Peer
) -> tuple[str, str, str | None, int | None, int | None, int | None]:
    """Build validation parameters for update, using existing peer values as defaults.

    Args:
        request: Update request with optional fields.
        peer: Existing peer to use for default values.

    Returns:
        Tuple of (remote_ip, ike_version, dpd_action, dpd_delay, dpd_timeout, rekey_time).
    """
    return (
        request.remoteIp if request.remoteIp is not None else peer.remoteIp,
        request.ikeVersion if request.ikeVersion is not None else peer.ikeVersion,
        request.dpdAction if request.dpdAction is not None else peer.dpdAction,
        request.dpdDelay if request.dpdDelay is not None else peer.dpdDelay,
        request.dpdTimeout if request.dpdTimeout is not None else peer.dpdTimeout,
        request.rekeyTime if request.rekeyTime is not None else peer.rekeyTime,
    )


def _configure_peer_in_daemon(peer: Peer, decrypted_psk: str) -> dict | None:
    """Send peer configuration to daemon for strongSwan setup.

    Returns daemon response or None if daemon unavailable.
    """
    try:
        response = send_command(
            "configure_peer",
            {
                "name": peer.name,
                "remote_ip": peer.remoteIp,
                "psk": decrypted_psk,
                "ike_version": peer.ikeVersion,
                "dpd_action": peer.dpdAction,
                "dpd_delay": peer.dpdDelay,
                "dpd_timeout": peer.dpdTimeout,
                "rekey_time": peer.rekeyTime,
            },
        )
        return response
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        logger.warning(
            f"Daemon not available for peer {peer.name} configuration: {e}. "
            f"Configuration saved to database only."
        )
        return None


def _should_emit_negotiating(status: str, message: str) -> bool:
    """Determine whether to emit a negotiating status event."""
    if status != "success":
        return False
    lowered = message.lower()
    return "already established" not in lowered and "already installed" not in lowered


async def _emit_tunnel_status_down(peer_id: int, peer_name: str) -> None:
    """Best-effort WebSocket emission for tunnel down state."""
    try:
        manager = get_monitoring_ws_manager()
        await manager.broadcast(
            {
                "type": "tunnel.status_changed",
                "data": {
                    "peerId": peer_id,
                    "peerName": peer_name,
                    "status": "down",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
    except Exception as e:
        logger.warning(
            "Failed to broadcast down status for peer %s (%s): %s",
            peer_name,
            peer_id,
            e,
        )


async def _broadcast_config_change(action: str, peer_id: int) -> None:
    """Best-effort WebSocket broadcast for peer config changes."""
    try:
        manager = get_monitoring_ws_manager()
        await manager.broadcast(
            {
                "type": "peer.config_changed",
                "data": {"action": action, "peerId": peer_id},
            }
        )
    except Exception as e:
        logger.warning("Failed to broadcast peer config change: %s", e)


@router.post("", response_model=PeerEnvelope, status_code=201)
async def create_peer_endpoint(
    request: PeerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerEnvelope:
    """Create a new IPsec peer configuration."""
    # Validate peer configuration
    is_valid, error_msg = validate_peer_config(
        remote_ip=request.remoteIp,
        ike_version=request.ikeVersion,
        dpd_action=request.dpdAction,
        dpd_delay=request.dpdDelay,
        dpd_timeout=request.dpdTimeout,
        rekey_time=request.rekeyTime,
    )
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=create_rfc7807_error(
                status=422,
                title="Validation Error",
                detail=error_msg,
                instance="/api/v1/peers",
            ),
        )

    # Check for duplicate name
    existing = get_peer_by_name(db, request.name)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=create_rfc7807_error(
                status=409,
                title="Conflict",
                detail=f"Peer with name '{request.name}' already exists",
                instance="/api/v1/peers",
            ),
        )

    # Create peer with encrypted PSK
    peer = create_peer(
        session=db,
        name=request.name,
        remote_ip=request.remoteIp,
        psk_plaintext=request.psk,
        ike_version=request.ikeVersion,
        enabled=request.enabled,
        dpd_action=request.dpdAction,
        dpd_delay=request.dpdDelay,
        dpd_timeout=request.dpdTimeout,
        rekey_time=request.rekeyTime,
    )

    # Configure in daemon (best-effort) - skip if peer is disabled
    daemon_response = None
    if peer.enabled:
        daemon_response = _configure_peer_in_daemon(peer, request.psk)

    meta = {"daemonAvailable": daemon_response is not None if peer.enabled else None}
    if peer.enabled and daemon_response is None:
        meta["warning"] = "Configuration saved to database only (daemon unavailable)"
    elif not peer.enabled:
        meta["warning"] = "Peer created in disabled state (daemon not configured)"

    data = PeerResponse.model_validate(peer)
    await _broadcast_config_change("created", peer.peerId)
    return PeerEnvelope(data=data, meta=meta)


@router.get("", response_model=PeerListEnvelope)
def list_peers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerListEnvelope:
    """List all IPsec peer configurations."""
    peers = get_all_peers(db)
    data = [PeerResponse.model_validate(p) for p in peers]
    return PeerListEnvelope(data=data, meta={"count": len(data)})


@router.get("/{peer_id}", response_model=PeerEnvelope)
def get_peer(
    peer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerEnvelope:
    """Get a specific peer configuration by ID."""
    peer = get_peer_by_id(db, peer_id)
    if peer is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Peer with ID {peer_id} not found",
                instance=f"/api/v1/peers/{peer_id}",
            ),
        )
    data = PeerResponse.model_validate(peer)
    return PeerEnvelope(data=data, meta={})


@router.put("/{peer_id}", response_model=PeerEnvelope)
async def update_peer_endpoint(
    peer_id: int,
    request: PeerUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerEnvelope:
    """Update an existing peer configuration."""
    peer = get_peer_by_id(db, peer_id)
    if peer is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Peer with ID {peer_id} not found",
                instance=f"/api/v1/peers/{peer_id}",
            ),
        )

    # Build validation params using existing values as defaults
    validation_params = _build_validation_params_for_update(request, peer)
    is_valid, error_msg = validate_peer_config(
        remote_ip=validation_params[0],
        ike_version=validation_params[1],
        dpd_action=validation_params[2],
        dpd_delay=validation_params[3],
        dpd_timeout=validation_params[4],
        rekey_time=validation_params[5],
    )
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=create_rfc7807_error(
                status=422,
                title="Validation Error",
                detail=error_msg,
                instance=f"/api/v1/peers/{peer_id}",
            ),
        )

    # Check name uniqueness if changing name
    if request.name is not None and request.name != peer.name:
        existing = get_peer_by_name(db, request.name)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=create_rfc7807_error(
                    status=409,
                    title="Conflict",
                    detail=f"Peer with name '{request.name}' already exists",
                    instance=f"/api/v1/peers/{peer_id}",
                ),
            )

    # Detect enable state transition before update
    old_enabled = peer.enabled
    new_enabled = request.enabled if request.enabled is not None else old_enabled
    is_disabling = old_enabled and not new_enabled
    is_enabling = not old_enabled and new_enabled

    updated = update_peer(
        session=db,
        peer=peer,
        name=request.name,
        remote_ip=request.remoteIp,
        psk_plaintext=request.psk,
        ike_version=request.ikeVersion,
        enabled=request.enabled,
        dpd_action=request.dpdAction,
        dpd_delay=request.dpdDelay,
        dpd_timeout=request.dpdTimeout,
        rekey_time=request.rekeyTime,
    )

    meta: dict = {}

    # Handle enable state transitions
    if is_disabling:
        # Peer is being disabled - teardown tunnel and remove config (best-effort)
        logger.info(f"Disabling peer {updated.name} - tearing down tunnel")
        daemon_available = True
        teardown_result: dict | None = None
        remove_result: dict | None = None

        # Teardown tunnel (best-effort)
        try:
            response = send_command("teardown_peer", {"name": updated.name})
            teardown_result = response.get("result", {})
            logger.info(f"Tunnel torn down for peer {updated.name}")
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
            daemon_available = False
            logger.warning(f"Could not teardown tunnel for peer {updated.name}: {e}")

        # Remove strongSwan config (best-effort)
        try:
            response = send_command("remove_peer_config", {"name": updated.name})
            remove_result = response.get("result", {})
            logger.info(f"Config removed for peer {updated.name}")
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
            daemon_available = False
            logger.warning(f"Could not remove config for peer {updated.name}: {e}")

        meta["daemonAvailable"] = daemon_available
        teardown_message = (teardown_result or {}).get("message")
        remove_message = (remove_result or {}).get("message")
        message_parts = ["Peer disabled"]
        if teardown_message:
            message_parts.append(teardown_message)
        if remove_message:
            message_parts.append(remove_message)
        if not daemon_available:
            message_parts.append("daemon unavailable for part of cleanup")
        meta["warning"] = " | ".join(message_parts)
        await _emit_tunnel_status_down(updated.peerId, updated.name)

    elif is_enabling:
        # Peer is being enabled - configure in daemon (best-effort)
        logger.info(f"Enabling peer {updated.name} - configuring in daemon")
        decrypted_psk = get_decrypted_psk(updated)
        daemon_response = _configure_peer_in_daemon(updated, decrypted_psk)

        meta["daemonAvailable"] = daemon_response is not None
        if daemon_response is None:
            meta["warning"] = "Peer enabled but daemon unavailable - configuration saved to database only"
        else:
            # Re-sync routes for enabled peers (best-effort)
            try:
                routes = get_routes_for_peer(db, updated.peerId)
                route_dicts = [
                    {"destination_cidr": route.destinationCidr} for route in routes
                ]
                send_command(
                    "update_routes",
                    {"peer_name": updated.name, "routes": route_dicts},
                )
                logger.info(f"Peer {updated.name} enabled and routes synced")
            except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
                logger.warning(f"Could not sync routes for peer {updated.name}: {e}")
                meta["warning"] = (
                    "Peer enabled and configured, but route sync failed (best-effort)"
                )

    elif updated.enabled:
        # Regular update for enabled peer - re-configure in daemon
        decrypted_psk = get_decrypted_psk(updated)
        daemon_response = _configure_peer_in_daemon(updated, decrypted_psk)

        meta["daemonAvailable"] = daemon_response is not None
        if daemon_response is None:
            meta["warning"] = "Configuration saved to database only (daemon unavailable)"

    else:
        # Regular update for disabled peer - no daemon operations
        meta["daemonAvailable"] = None
        meta["warning"] = "Peer is disabled - daemon not updated"

    data = PeerResponse.model_validate(updated)
    await _broadcast_config_change("updated", updated.peerId)
    return PeerEnvelope(data=data, meta=meta)


@router.post("/{peer_id}/initiate", response_model=PeerEnvelope)
async def initiate_peer_tunnel(
    peer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerEnvelope:
    """Initiate a tunnel for an IPsec peer."""
    peer = get_peer_by_id(db, peer_id)
    if peer is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Peer with ID {peer_id} not found",
                instance=f"/api/v1/peers/{peer_id}/initiate",
            ),
        )

    # Validate peer is ready for initiation
    if peer.operationalStatus != "ready":
        raise HTTPException(
            status_code=409,
            detail=create_rfc7807_error(
                status=409,
                title="Conflict",
                detail=f"Peer is not ready for initiation (status: {peer.operationalStatus})",
                instance=f"/api/v1/peers/{peer_id}/initiate",
            ),
        )

    # Attempt to initiate tunnel via daemon
    try:
        logger.info(f"Initiating tunnel for peer {peer.name} (ID: {peer_id})")
        response = send_command("initiate_peer", {"name": peer.name})
        daemon_status = response.get("status", "ok")
        initiation_result = response.get("result", {}) if daemon_status == "ok" else {}
        initiation_status = initiation_result.get("status", "error")
        initiation_message = initiation_result.get(
            "message",
            "Daemon returned an error while initiating the tunnel",
        )

        logger.info(
            f"Tunnel initiation for peer {peer.name} completed: {initiation_status}"
        )

        if initiation_status == "warning":
            raise HTTPException(
                status_code=503,
                detail=create_rfc7807_error(
                    status=503,
                    title="Service Unavailable",
                    detail=initiation_message,
                    instance=f"/api/v1/peers/{peer_id}/initiate",
                ),
            )

        if _should_emit_negotiating(initiation_status, initiation_message):
            try:
                manager = get_monitoring_ws_manager()
                await manager.broadcast(
                    {
                        "type": "tunnel.status_changed",
                        "data": {
                            "peerId": peer.peerId,
                            "peerName": peer.name,
                            "status": "negotiating",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )
            except Exception as e:
                logger.warning(
                    "Failed to broadcast negotiating status for peer %s: %s",
                    peer.name,
                    e,
                )

        data = PeerResponse.model_validate(peer)
        meta = {
            "daemonAvailable": daemon_status == "ok",
            "initiationStatus": initiation_status,
            "initiationMessage": initiation_message,
        }
        if "warning" in initiation_result:
            meta["warning"] = initiation_result["warning"]
        return PeerEnvelope(data=data, meta=meta)

    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(f"Daemon unavailable for peer {peer.name} tunnel initiation: {e}")
        raise HTTPException(
            status_code=503,
            detail=create_rfc7807_error(
                status=503,
                title="Service Unavailable",
                detail="Daemon is not available for tunnel initiation",
                instance=f"/api/v1/peers/{peer_id}/initiate",
            ),
        )


@router.delete("/{peer_id}", response_model=PeerEnvelope)
async def delete_peer_endpoint(
    peer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PeerEnvelope:
    """Delete an IPsec peer configuration."""
    peer = get_peer_by_id(db, peer_id)
    if peer is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Peer with ID {peer_id} not found",
                instance=f"/api/v1/peers/{peer_id}",
            ),
        )

    peer_name = peer.name

    deleted_data = PeerResponse.model_validate(peer)

    # Delete peer from database first (with cascade route deletion)
    # This is transactional and can be rolled back if it fails
    _, routes_deleted = delete_peer(db, peer_id)

    if routes_deleted > 0:
        logger.info(
            f"Deleted peer {peer_name} (ID: {peer_id}) "
            f"and {routes_deleted} associated route(s)"
        )
    else:
        logger.info(f"Deleted peer {peer_name} (ID: {peer_id})")

    # After successful DB deletion, clean up daemon state (best-effort)
    # These operations are logged but don't fail the API response

    daemon_available = True
    teardown_result: dict | None = None
    remove_result: dict | None = None

    # Teardown active tunnel (best-effort via daemon)
    try:
        response = send_command("teardown_peer", {"name": peer_name})
        teardown_result = response.get("result", {})
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        daemon_available = False
        logger.warning(
            f"Daemon not available for tunnel teardown of peer {peer_name}: {e}"
        )

    # Remove strongSwan config file (best-effort via daemon)
    try:
        response = send_command("remove_peer_config", {"name": peer_name})
        remove_result = response.get("result", {})
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        daemon_available = False
        logger.warning(
            f"Daemon not available for config removal of peer {peer_name}: {e}"
        )

    await _emit_tunnel_status_down(peer_id, peer_name)

    teardown_message = (teardown_result or {}).get("message")
    remove_message = (remove_result or {}).get("message")
    warning_parts = []
    if teardown_message:
        warning_parts.append(teardown_message)
    if remove_message:
        warning_parts.append(remove_message)
    if not daemon_available:
        warning_parts.append("daemon unavailable for part of cleanup")

    meta: dict = {"daemonAvailable": daemon_available, "routesDeleted": routes_deleted}
    if warning_parts:
        meta["warning"] = " | ".join(warning_parts)

    await _broadcast_config_change("deleted", peer_id)
    return PeerEnvelope(data=deleted_data, meta=meta)
