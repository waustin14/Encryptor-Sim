"""Route service for CRUD operations and validation.

Business logic for creating, reading, updating, and listing
route configurations associated with IPsec peers.
"""

import ipaddress
import logging

from sqlalchemy.orm import Session

from backend.app.models.peer import Peer
from backend.app.models.route import Route

logger = logging.getLogger(__name__)


def validate_cidr(cidr: str) -> tuple[bool, str, str]:
    """Validate and normalize CIDR format.

    Returns:
        Tuple of (is_valid, error_message, normalized_cidr).
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        if network.version != 4:
            return False, "Only IPv4 CIDRs are supported", ""
        return True, "", str(network)
    except ValueError as e:
        return False, f"Invalid CIDR format: {cidr} ({e})", ""


def get_peer_by_id(session: Session, peer_id: int) -> Peer | None:
    """Get peer by ID for validation."""
    return session.query(Peer).filter(Peer.peerId == peer_id).first()


def create_route(
    session: Session,
    peer_id: int,
    destination_cidr: str,
) -> Route:
    """Create a new route for a peer.

    Args:
        session: Database session.
        peer_id: ID of the associated peer.
        destination_cidr: Destination CIDR (already validated/normalized).

    Returns:
        Created Route instance.
    """
    route = Route(
        peerId=peer_id,
        destinationCidr=destination_cidr,
    )
    session.add(route)
    session.commit()
    session.refresh(route)
    return route


def update_route(
    session: Session,
    route: Route,
    destination_cidr: str | None = None,
) -> Route:
    """Update an existing route.

    Args:
        session: Database session.
        route: Existing Route instance to update.
        destination_cidr: New CIDR value (None = no change).

    Returns:
        Updated Route instance.
    """
    if destination_cidr is not None:
        route.destinationCidr = destination_cidr

    session.commit()
    session.refresh(route)
    return route


def get_route_by_id(session: Session, route_id: int) -> Route | None:
    """Get route by ID."""
    return session.query(Route).filter(Route.routeId == route_id).first()


def get_all_routes(session: Session, peer_id: int | None = None) -> list[Route]:
    """Get all routes, optionally filtered by peer ID.

    Args:
        session: Database session.
        peer_id: Optional peer ID to filter by.

    Returns:
        List of Route instances.
    """
    query = session.query(Route).order_by(Route.routeId)
    if peer_id is not None:
        query = query.filter(Route.peerId == peer_id)
    return list(query.all())


def delete_route(session: Session, route_id: int) -> tuple[str, int]:
    """Delete a route and return peer info for traffic selector update.

    Args:
        session: Database session.
        route_id: Route ID to delete.

    Returns:
        Tuple of (peer_name, peer_id) for daemon IPC update.

    Raises:
        ValueError: If route not found (caller should map to 404).
    """
    route = session.query(Route).filter(Route.routeId == route_id).first()
    if route is None:
        raise ValueError(f"Route with ID {route_id} not found")

    peer_name = route.peer.name if route.peer else "unknown"
    peer_id = route.peerId

    session.delete(route)
    session.commit()

    return peer_name, peer_id


def get_routes_for_peer(session: Session, peer_id: int) -> list[Route]:
    """Get all routes for a specific peer.

    Args:
        session: Database session.
        peer_id: Peer ID.

    Returns:
        List of Route instances for the peer.
    """
    return list(
        session.query(Route)
        .filter(Route.peerId == peer_id)
        .order_by(Route.routeId)
        .all()
    )
