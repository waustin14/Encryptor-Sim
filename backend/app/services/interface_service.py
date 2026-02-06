"""Interface configuration service.

Business logic for validating and persisting interface configurations.
"""

import ipaddress

from sqlalchemy.orm import Session

from backend.app.models.interface import Interface


def validate_ip_address(ip: str) -> tuple[bool, str]:
    """Validate IPv4 address format and restrictions.

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

    return True, ""


def validate_netmask(netmask: str) -> tuple[bool, str]:
    """Validate IPv4 netmask in dotted notation.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        ipaddress.IPv4Address(netmask)
    except (ipaddress.AddressValueError, ValueError):
        return False, f"Invalid netmask format: {netmask}"

    # Verify it's a valid netmask by trying to create a network with it
    try:
        ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
    except (ValueError, ipaddress.NetmaskValueError):
        return False, f"Invalid netmask: {netmask}"

    return True, ""


def validate_gateway(
    gateway: str, ip_address: str, netmask: str
) -> tuple[bool, str]:
    """Validate gateway is a valid IP and in the same subnet.

    Returns:
        Tuple of (is_valid, error_message).
    """
    try:
        ipaddress.IPv4Address(gateway)
    except (ipaddress.AddressValueError, ValueError):
        return False, f"Invalid gateway format: {gateway}"

    # Check gateway is in the same subnet as the IP address
    try:
        network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
        gw_addr = ipaddress.IPv4Address(gateway)
        if gw_addr not in network:
            return False, (
                f"Gateway {gateway} is not in the same subnet "
                f"as {ip_address}/{netmask}"
            )
    except (ValueError, ipaddress.AddressValueError):
        pass  # Individual validations will catch format issues

    return True, ""


def validate_interface_config(
    ip_address: str, netmask: str, gateway: str
) -> tuple[bool, str]:
    """Run all validations on interface configuration.

    Returns:
        Tuple of (is_valid, error_message).
    """
    valid, msg = validate_ip_address(ip_address)
    if not valid:
        return False, msg

    valid, msg = validate_netmask(netmask)
    if not valid:
        return False, msg

    valid, msg = validate_gateway(gateway, ip_address, netmask)
    if not valid:
        return False, msg

    return True, ""


def get_all_interfaces(session: Session) -> list[Interface]:
    """Get all interface configurations."""
    return list(session.query(Interface).order_by(Interface.interfaceId).all())


def get_interface_by_name(session: Session, name: str) -> Interface | None:
    """Get interface by name (case-insensitive)."""
    return (
        session.query(Interface)
        .filter(Interface.name == name.upper())
        .first()
    )


def update_interface_config(
    session: Session,
    interface: Interface,
    ip_address: str,
    netmask: str,
    gateway: str,
) -> Interface:
    """Update interface IP configuration in the database."""
    interface.ipAddress = ip_address
    interface.netmask = netmask
    interface.gateway = gateway
    session.commit()
    session.refresh(interface)
    return interface


def rollback_interface_config(
    session: Session,
    interface: Interface,
    prev_ip: str | None,
    prev_netmask: str | None,
    prev_gateway: str | None,
) -> None:
    """Rollback interface configuration to previous values."""
    interface.ipAddress = prev_ip
    interface.netmask = prev_netmask
    interface.gateway = prev_gateway
    session.commit()
    session.refresh(interface)
