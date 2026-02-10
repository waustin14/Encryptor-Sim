"""XFRM interface operations for IPsec tunnel routing.

Creates and manages XFRM interfaces (xfrmi) in the default namespace
to route decrypted traffic between ns_ct (strongSwan) and ns_pt (plaintext).
"""

import logging
import subprocess
from collections.abc import Callable

logger = logging.getLogger(__name__)

Runner = Callable[..., subprocess.CompletedProcess]

CT_NAMESPACE = "ns_ct"
CT_DEVICE = "eth1"
PT_NAMESPACE = "ns_pt"
VETH_DEFAULT_IP = "169.254.0.1"
XFRM_MTU = 1400


def _if_id_from_peer_id(peer_id: int) -> int:
    """Return the XFRM if_id for a given peer_id (1:1 mapping)."""
    return peer_id


def _xfrm_dev_name(peer_id: int) -> str:
    """Return the xfrmi device name for a peer."""
    return f"xfrm{peer_id}"


def create_xfrm_interface(
    peer_id: int,
    if_id: int,
    *,
    runner: Runner = subprocess.run,
) -> str:
    """Create an XFRM interface linked to ns_ct's SA database.

    The xfrmi device must be created inside ns_ct (where strongSwan installs
    IPsec SAs) so the kernel can match packets against the correct SA database.
    It is then moved to the default namespace for routing, but retains its
    link to ns_ct's XFRM state.

    Args:
        peer_id: Peer identifier (used for device naming).
        if_id: XFRM interface ID (matches if_id_in/if_id_out in swanctl config).
        runner: Command runner (injectable for testing).

    Returns:
        The created interface name (e.g. "xfrm1").
    """
    dev_name = _xfrm_dev_name(peer_id)

    # Delete existing interface if present (idempotent)
    runner(
        ["ip", "link", "del", dev_name],
        capture_output=True,
        check=False,
    )

    # Create xfrmi device inside ns_ct, linked to the CT device (eth1).
    # This binds the interface to ns_ct's XFRM SA/SP database.
    runner(
        [
            "ip", "netns", "exec", CT_NAMESPACE,
            "ip", "link", "add", dev_name,
            "type", "xfrm",
            "dev", CT_DEVICE,
            "if_id", str(if_id),
        ],
        capture_output=True,
        check=True,
    )

    # Move xfrmi device from ns_ct to the default namespace (PID 1).
    # The interface retains its link-netns association with ns_ct.
    runner(
        [
            "ip", "netns", "exec", CT_NAMESPACE,
            "ip", "link", "set", dev_name, "netns", "1",
        ],
        capture_output=True,
        check=True,
    )

    # Set MTU to account for IPsec overhead
    runner(
        ["ip", "link", "set", dev_name, "mtu", str(XFRM_MTU)],
        capture_output=True,
        check=True,
    )

    # Bring interface up
    runner(
        ["ip", "link", "set", dev_name, "up"],
        capture_output=True,
        check=True,
    )

    logger.info(f"Created XFRM interface {dev_name} with if_id={if_id}")
    return dev_name


def delete_xfrm_interface(
    peer_id: int,
    *,
    runner: Runner = subprocess.run,
) -> None:
    """Delete an XFRM interface if it exists.

    Idempotent: succeeds even if the interface doesn't exist.

    Args:
        peer_id: Peer identifier.
        runner: Command runner (injectable for testing).
    """
    dev_name = _xfrm_dev_name(peer_id)
    result = runner(
        ["ip", "link", "del", dev_name],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        logger.info(f"Deleted XFRM interface {dev_name}")
    else:
        logger.debug(f"XFRM interface {dev_name} not found (already deleted)")


def add_tunnel_route(
    peer_id: int,
    destination: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    """Add a route in the default namespace pointing to an xfrmi device.

    Args:
        peer_id: Peer identifier.
        destination: Destination CIDR (e.g. "192.168.1.0/24").
        runner: Command runner (injectable for testing).
    """
    dev_name = _xfrm_dev_name(peer_id)
    runner(
        ["ip", "route", "replace", destination, "dev", dev_name],
        capture_output=True,
        check=True,
    )
    logger.info(f"Added route {destination} via {dev_name}")


def remove_tunnel_routes(
    peer_id: int,
    *,
    runner: Runner = subprocess.run,
) -> None:
    """Remove all routes pointing to an xfrmi device.

    Args:
        peer_id: Peer identifier.
        runner: Command runner (injectable for testing).
    """
    dev_name = _xfrm_dev_name(peer_id)
    # List routes for this device and remove them
    result = runner(
        ["ip", "route", "show", "dev", dev_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return

    for line in result.stdout.strip().splitlines():
        dest = line.split()[0]
        runner(
            ["ip", "route", "del", dest, "dev", dev_name],
            capture_output=True,
            check=False,
        )
        logger.info(f"Removed route {dest} via {dev_name}")


def add_pt_return_route(
    destination: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    """Add a return route in ns_pt via the veth pair.

    Routes traffic destined for tunnel subnets back through the default
    namespace where xfrmi interfaces handle encryption.

    Args:
        destination: Destination CIDR (e.g. "192.168.1.0/24").
        runner: Command runner (injectable for testing).
    """
    runner(
        [
            "ip", "netns", "exec", PT_NAMESPACE,
            "ip", "route", "replace", destination, "via", VETH_DEFAULT_IP,
        ],
        capture_output=True,
        check=True,
    )
    logger.info(f"Added ns_pt return route {destination} via {VETH_DEFAULT_IP}")


def remove_pt_return_route(
    destination: str,
    *,
    runner: Runner = subprocess.run,
) -> None:
    """Remove a return route from ns_pt.

    Args:
        destination: Destination CIDR to remove.
        runner: Command runner (injectable for testing).
    """
    result = runner(
        [
            "ip", "netns", "exec", PT_NAMESPACE,
            "ip", "route", "del", destination, "via", VETH_DEFAULT_IP,
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        logger.info(f"Removed ns_pt return route {destination}")
    else:
        logger.debug(f"ns_pt return route {destination} not found")
