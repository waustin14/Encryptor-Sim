"""Route configuration API endpoints.

Provides endpoints for creating, listing, viewing, and updating
route configurations associated with IPsec peers.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_session
from backend.app.models.user import User
from backend.app.schemas.route import (
    RouteCreateRequest,
    RouteEnvelope,
    RouteListEnvelope,
    RouteResponse,
    RouteUpdateRequest,
)
from backend.app.services.daemon_ipc import send_command
from backend.app.services.route_service import (
    create_route,
    delete_route,
    get_all_routes,
    get_peer_by_id,
    get_route_by_id,
    get_routes_for_peer,
    update_route,
)
from backend.app.utils.rfc7807 import create_rfc7807_error
from backend.app.ws.monitoring import get_monitoring_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])


async def _broadcast_route_config_change(action: str, route_id: int, peer_id: int) -> None:
    """Best-effort WebSocket broadcast for route config changes."""
    try:
        manager = get_monitoring_ws_manager()
        await manager.broadcast(
            {
                "type": "route.config_changed",
                "data": {"action": action, "routeId": route_id, "peerId": peer_id},
            }
        )
    except Exception as e:
        logger.warning("Failed to broadcast route config change: %s", e)


def _build_route_response(route) -> RouteResponse:
    """Build a RouteResponse with peer name resolved."""
    return RouteResponse(
        routeId=route.routeId,
        peerId=route.peerId,
        peerName=route.peer.name if route.peer else "unknown",
        destinationCidr=route.destinationCidr,
        createdAt=route.createdAt,
        updatedAt=route.updatedAt,
    )


def _update_routes_in_daemon(peer_name: str, routes: list, peer_id: int | None = None) -> dict | None:
    """Send route configuration to daemon for strongSwan traffic selector update.

    Best-effort: logs errors but does not fail the API call.
    """
    try:
        route_dicts = [{"destination_cidr": r.destinationCidr} for r in routes]
        payload: dict = {
            "peer_name": peer_name,
            "routes": route_dicts,
        }
        if peer_id is not None:
            payload["peer_id"] = peer_id
        response = send_command(
            "update_routes",
            payload,
        )
        return response
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        logger.warning(
            f"Daemon not available for route update on peer {peer_name}: {e}. "
            f"Configuration saved to database only."
        )
        return None


@router.post("", response_model=RouteEnvelope, status_code=201)
async def create_route_endpoint(
    request: RouteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RouteEnvelope:
    """Create a new route for a peer."""
    # Validate peer exists
    peer = get_peer_by_id(db, request.peerId)
    if peer is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Peer with ID {request.peerId} not found",
                instance="/api/v1/routes",
            ),
        )

    route = create_route(
        session=db,
        peer_id=request.peerId,
        destination_cidr=request.destinationCidr,
    )

    # Update daemon with all routes for this peer (best-effort)
    # Skip daemon update if peer is disabled
    meta: dict = {}
    if peer.enabled:
        all_peer_routes = get_routes_for_peer(db, request.peerId)
        daemon_response = _update_routes_in_daemon(peer.name, all_peer_routes, peer_id=peer.peerId)

        meta["daemonAvailable"] = daemon_response is not None
        if daemon_response is None:
            meta["warning"] = "Configuration saved to database only (daemon unavailable)"
    else:
        meta["daemonAvailable"] = None
        meta["warning"] = "Peer is disabled - daemon not updated"

    data = _build_route_response(route)
    await _broadcast_route_config_change("created", route.routeId, request.peerId)
    return RouteEnvelope(data=data, meta=meta)


@router.get("", response_model=RouteListEnvelope)
def list_routes(
    peerId: Optional[int] = Query(default=None, description="Filter routes by peer ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RouteListEnvelope:
    """List all routes, optionally filtered by peer ID."""
    routes = get_all_routes(db, peer_id=peerId)
    data = [_build_route_response(r) for r in routes]
    return RouteListEnvelope(data=data, meta={"count": len(data)})


@router.get("/{route_id}", response_model=RouteEnvelope)
def get_route(
    route_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RouteEnvelope:
    """Get a specific route by ID."""
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Route with ID {route_id} not found",
                instance=f"/api/v1/routes/{route_id}",
            ),
        )
    data = _build_route_response(route)
    return RouteEnvelope(data=data, meta={})


@router.put("/{route_id}", response_model=RouteEnvelope)
async def update_route_endpoint(
    route_id: int,
    request: RouteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RouteEnvelope:
    """Update an existing route's destination CIDR."""
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Route with ID {route_id} not found",
                instance=f"/api/v1/routes/{route_id}",
            ),
        )

    updated = update_route(
        session=db,
        route=route,
        destination_cidr=request.destinationCidr,
    )

    # Update daemon with all routes for this peer (best-effort)
    # Skip daemon update if peer is disabled
    peer = get_peer_by_id(db, updated.peerId)
    peer_name = peer.name if peer else "unknown"

    meta: dict = {}
    if peer and peer.enabled:
        all_peer_routes = get_routes_for_peer(db, updated.peerId)
        daemon_response = _update_routes_in_daemon(peer_name, all_peer_routes, peer_id=updated.peerId)

        meta["daemonAvailable"] = daemon_response is not None
        if daemon_response is None:
            meta["warning"] = "Configuration saved to database only (daemon unavailable)"
    else:
        meta["daemonAvailable"] = None
        meta["warning"] = "Peer is disabled - daemon not updated"

    data = _build_route_response(updated)
    await _broadcast_route_config_change("updated", updated.routeId, updated.peerId)
    return RouteEnvelope(data=data, meta=meta)


@router.delete("/{route_id}", response_model=RouteEnvelope)
async def delete_route_endpoint(
    route_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> RouteEnvelope:
    """Delete a route."""
    # Fetch route before deletion to build response
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Route with ID {route_id} not found",
                instance=f"/api/v1/routes/{route_id}",
            ),
        )

    deleted_data = _build_route_response(route)

    try:
        peer_name, peer_id = delete_route(db, route_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Route with ID {route_id} not found",
                instance=f"/api/v1/routes/{route_id}",
            ),
        )

    # Update daemon with remaining routes for this peer (best-effort)
    meta: dict = {}
    peer = get_peer_by_id(db, peer_id)
    if peer and peer.enabled:
        remaining_routes = get_routes_for_peer(db, peer_id)
        daemon_response = _update_routes_in_daemon(peer_name, remaining_routes, peer_id=peer_id)
        meta["daemonAvailable"] = daemon_response is not None
        if daemon_response is None:
            meta["warning"] = "Route deleted from database but daemon unavailable for traffic selector update"
    elif peer and not peer.enabled:
        meta["daemonAvailable"] = None
        meta["warning"] = "Peer is disabled - daemon not updated"
    else:
        meta["daemonAvailable"] = None

    await _broadcast_route_config_change("deleted", route_id, peer_id)
    return RouteEnvelope(data=deleted_data, meta=meta)
