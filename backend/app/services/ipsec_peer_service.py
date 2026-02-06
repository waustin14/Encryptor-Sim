"""IPsec peer service for validation and CRUD operations.

Business logic for creating, reading, updating, validating,
and deleting peer configurations.
"""

import ipaddress
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.app.models.peer import Peer
from backend.app.services.psk_crypto import decrypt_psk, encrypt_psk


# Validation constants
VALID_IKE_VERSIONS = ("ikev1", "ikev2")
VALID_DPD_ACTIONS = ("clear", "hold", "restart")
DPD_DELAY_MIN = 10
DPD_DELAY_MAX = 300
DPD_TIMEOUT_MIN = 10
DPD_TIMEOUT_MAX = 600
REKEY_TIME_MIN = 300
REKEY_TIME_MAX = 86400


def validate_remote_ip(ip: str) -> tuple[bool, str]:
    """Validate remote IPv4 address format.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        addr = ipaddress.IPv4Address(ip)
    except (ipaddress.AddressValueError, ValueError):
        return False, f"Invalid IP address format: {ip}"

    if addr.is_unspecified:
        return False, f"Reserved IP address not allowed: {ip}"

    if str(addr) == "255.255.255.255":
        return False, f"Broadcast IP address not allowed: {ip}"

    if addr.is_loopback:
        return False, f"Loopback IP address not allowed: {ip}"

    return True, ""


def validate_ike_version(version: str) -> tuple[bool, str]:
    """Validate IKE version string.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if version.lower() not in VALID_IKE_VERSIONS:
        return False, (
            f"Invalid IKE version: {version}. Must be one of: "
            f"{', '.join(VALID_IKE_VERSIONS)}"
        )
    return True, ""


def validate_dpd_params(
    action: str | None, delay: int | None, timeout: int | None
) -> tuple[bool, str]:
    """Validate DPD parameters.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if action is not None and action not in VALID_DPD_ACTIONS:
        return False, (
            f"Invalid DPD action: {action}. Must be one of: "
            f"{', '.join(VALID_DPD_ACTIONS)}"
        )

    if delay is not None:
        if not isinstance(delay, int) or delay < DPD_DELAY_MIN or delay > DPD_DELAY_MAX:
            return False, (
                f"DPD delay must be an integer between "
                f"{DPD_DELAY_MIN} and {DPD_DELAY_MAX} seconds"
            )

    if timeout is not None:
        if (
            not isinstance(timeout, int)
            or timeout < DPD_TIMEOUT_MIN
            or timeout > DPD_TIMEOUT_MAX
        ):
            return False, (
                f"DPD timeout must be an integer between "
                f"{DPD_TIMEOUT_MIN} and {DPD_TIMEOUT_MAX} seconds"
            )

    if delay is not None and timeout is not None and timeout <= delay:
        return False, "DPD timeout must be greater than DPD delay"

    return True, ""


def validate_rekey_time(rekey: int | None) -> tuple[bool, str]:
    """Validate rekey time.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if rekey is not None:
        if (
            not isinstance(rekey, int)
            or rekey < REKEY_TIME_MIN
            or rekey > REKEY_TIME_MAX
        ):
            return False, (
                f"Rekey time must be an integer between "
                f"{REKEY_TIME_MIN} and {REKEY_TIME_MAX} seconds"
            )
    return True, ""


def validate_peer_config(
    remote_ip: str,
    ike_version: str,
    dpd_action: str | None = None,
    dpd_delay: int | None = None,
    dpd_timeout: int | None = None,
    rekey_time: int | None = None,
) -> tuple[bool, str]:
    """Run all validations on peer configuration.

    Returns:
        Tuple of (is_valid, error_message).
    """
    valid, msg = validate_remote_ip(remote_ip)
    if not valid:
        return False, msg

    valid, msg = validate_ike_version(ike_version)
    if not valid:
        return False, msg

    valid, msg = validate_dpd_params(dpd_action, dpd_delay, dpd_timeout)
    if not valid:
        return False, msg

    valid, msg = validate_rekey_time(rekey_time)
    if not valid:
        return False, msg

    return True, ""


def get_all_peers(session: Session) -> list[Peer]:
    """Get all peer configurations."""
    return list(session.query(Peer).order_by(Peer.peerId).all())


def get_peer_by_id(session: Session, peer_id: int) -> Peer | None:
    """Get peer by ID."""
    return session.query(Peer).filter(Peer.peerId == peer_id).first()


def get_peer_by_name(session: Session, name: str) -> Peer | None:
    """Get peer by name."""
    return session.query(Peer).filter(Peer.name == name).first()


def create_peer(
    session: Session,
    name: str,
    remote_ip: str,
    psk_plaintext: str,
    ike_version: str,
    enabled: bool = True,
    dpd_action: str | None = "restart",
    dpd_delay: int | None = 30,
    dpd_timeout: int | None = 150,
    rekey_time: int | None = 3600,
) -> Peer:
    """Create a new peer with encrypted PSK.

    Args:
        session: Database session.
        name: Unique peer name.
        remote_ip: Remote IPv4 address.
        psk_plaintext: Pre-shared key (will be encrypted).
        ike_version: IKE version (ikev1 or ikev2).
        enabled: Whether peer is enabled (default True).
        dpd_action: DPD action.
        dpd_delay: DPD delay in seconds.
        dpd_timeout: DPD timeout in seconds.
        rekey_time: Rekey time in seconds.

    Returns:
        Created Peer instance.
    """
    encrypted_psk = encrypt_psk(psk_plaintext)

    peer = Peer(
        name=name,
        remoteIp=remote_ip,
        psk=encrypted_psk,
        ikeVersion=ike_version.lower(),
        enabled=enabled,
        dpdAction=dpd_action,
        dpdDelay=dpd_delay,
        dpdTimeout=dpd_timeout,
        rekeyTime=rekey_time,
    )
    session.add(peer)
    session.commit()
    session.refresh(peer)
    return peer


def update_peer(
    session: Session,
    peer: Peer,
    name: str | None = None,
    remote_ip: str | None = None,
    psk_plaintext: str | None = None,
    ike_version: str | None = None,
    enabled: bool | None = None,
    dpd_action: str | None = None,
    dpd_delay: int | None = None,
    dpd_timeout: int | None = None,
    rekey_time: int | None = None,
) -> Peer:
    """Update an existing peer configuration.

    Only updates fields that are provided (not None).

    Args:
        session: Database session.
        peer: Existing Peer instance to update.
        Other args: Fields to update (None = no change).

    Returns:
        Updated Peer instance.
    """
    if name is not None:
        peer.name = name
    if remote_ip is not None:
        peer.remoteIp = remote_ip
    if psk_plaintext is not None:
        peer.psk = encrypt_psk(psk_plaintext)
    if ike_version is not None:
        peer.ikeVersion = ike_version.lower()
    if enabled is not None:
        peer.enabled = enabled
    if dpd_action is not None:
        peer.dpdAction = dpd_action
    if dpd_delay is not None:
        peer.dpdDelay = dpd_delay
    if dpd_timeout is not None:
        peer.dpdTimeout = dpd_timeout
    if rekey_time is not None:
        peer.rekeyTime = rekey_time

    session.commit()
    session.refresh(peer)
    return peer


def cascade_delete_routes(session: Session, peer_id: int) -> int:
    """Delete all routes associated with a peer.

    Performs cascade deletion of routes before peer is removed.
    Returns the number of routes deleted.

    Args:
        session: Database session.
        peer_id: ID of the peer whose routes should be deleted.

    Returns:
        Number of routes deleted.
    """
    # Import Route model dynamically to avoid circular imports
    # and handle the case where Route model doesn't exist yet (Story 4.4)
    try:
        from backend.app.models.route import Route

        routes = session.query(Route).filter(Route.peerId == peer_id).all()
        count = len(routes)
        if count > 0:
            logger.warning(
                f"Cascade deleting {count} route(s) associated with peer ID {peer_id}"
            )
            for route in routes:
                session.delete(route)
        return count
    except (ImportError, ModuleNotFoundError):
        # Route model not yet implemented (Story 4.4)
        return 0


def delete_peer(session: Session, peer_id: int) -> tuple[Peer | None, int]:
    """Delete a peer by ID with cascade route deletion.

    Deletes associated routes first, then the peer.

    Args:
        session: Database session.
        peer_id: ID of the peer to delete.

    Returns:
        Tuple of (deleted Peer instance or None, routes deleted count).
    """
    peer = get_peer_by_id(session, peer_id)
    if peer is None:
        return None, 0

    # Cascade delete associated routes
    routes_deleted = cascade_delete_routes(session, peer_id)

    session.delete(peer)
    session.commit()
    return peer, routes_deleted


def get_decrypted_psk(peer: Peer) -> str:
    """Get the decrypted PSK for daemon communication.

    Args:
        peer: Peer instance with encrypted PSK.

    Returns:
        Decrypted PSK string.
    """
    return decrypt_psk(peer.psk)
