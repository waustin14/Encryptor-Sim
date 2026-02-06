"""Network interface configuration operations.

Applies IP configuration to namespace-specific interfaces via system commands.
Generates persistent network configuration files in /etc/netns/.
"""

import ipaddress
import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

Runner = Callable[..., subprocess.CompletedProcess]

# Valid interface name to namespace/device mappings
INTERFACE_MAP = {
    "CT": {"namespace": "ns_ct", "device": "eth1"},
    "PT": {"namespace": "ns_pt", "device": "eth2"},
    "MGMT": {"namespace": "ns_mgmt", "device": "eth0"},
}


def validate_interface_config(
    name: str, ip_address: str, netmask: str, gateway: str
) -> None:
    """Validate interface configuration parameters (defense-in-depth).

    Raises ValueError for invalid inputs.
    """
    name_upper = name.upper()
    if name_upper not in INTERFACE_MAP:
        raise ValueError(f"Unknown interface: {name}")

    try:
        addr = ipaddress.IPv4Address(ip_address)
    except (ipaddress.AddressValueError, ValueError):
        raise ValueError(f"Invalid IP address: {ip_address}")

    if addr.is_unspecified or str(addr) == "255.255.255.255":
        raise ValueError(f"Reserved IP address not allowed: {ip_address}")

    try:
        ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
    except (ValueError, ipaddress.NetmaskValueError):
        raise ValueError(f"Invalid netmask: {netmask}")

    try:
        gw = ipaddress.IPv4Address(gateway)
    except (ipaddress.AddressValueError, ValueError):
        raise ValueError(f"Invalid gateway: {gateway}")

    network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
    if gw not in network:
        raise ValueError(f"Gateway {gateway} not in subnet {network}")


def _netmask_to_prefix(netmask: str) -> int:
    """Convert dotted netmask to CIDR prefix length."""
    return ipaddress.IPv4Network(f"0.0.0.0/{netmask}").prefixlen


def configure_interface(
    name: str,
    ip_address: str,
    netmask: str,
    gateway: str,
    *,
    runner: Runner = subprocess.run,
    config_base_dir: str = "/etc/netns",
) -> dict[str, str]:
    """Configure a network interface in its namespace.

    Args:
        name: Interface name (CT, PT, MGMT).
        ip_address: IPv4 address.
        netmask: IPv4 netmask in dotted notation.
        gateway: IPv4 gateway address.
        runner: Command runner (injectable for testing).
        config_base_dir: Base directory for netns config files.

    Returns:
        Status dict with result details.

    Raises:
        ValueError: If configuration parameters are invalid.
        subprocess.CalledProcessError: If system commands fail.
    """
    name_upper = name.upper()
    validate_interface_config(name_upper, ip_address, netmask, gateway)

    mapping = INTERFACE_MAP[name_upper]
    namespace = mapping["namespace"]
    device = mapping["device"]
    prefix_len = _netmask_to_prefix(netmask)

    # Flush existing IP configuration
    runner(
        ["ip", "netns", "exec", namespace, "ip", "addr", "flush", "dev", device],
        check=True,
        capture_output=True,
    )

    # Add new IP address
    runner(
        [
            "ip", "netns", "exec", namespace, "ip", "addr", "add",
            f"{ip_address}/{prefix_len}", "dev", device,
        ],
        check=True,
        capture_output=True,
    )

    # Bring interface up
    runner(
        ["ip", "netns", "exec", namespace, "ip", "link", "set", device, "up"],
        check=True,
        capture_output=True,
    )

    # Delete existing default route (ignore errors if none exists)
    runner(
        ["ip", "netns", "exec", namespace, "ip", "route", "del", "default"],
        check=False,
        capture_output=True,
    )

    # Add default gateway
    runner(
        [
            "ip", "netns", "exec", namespace, "ip", "route", "add",
            "default", "via", gateway,
        ],
        check=True,
        capture_output=True,
    )

    # Write persistent configuration file
    write_netns_config(
        namespace, device, ip_address, netmask, gateway,
        base_dir=config_base_dir,
    )

    return {
        "status": "success",
        "message": "Interface configured successfully",
        "namespace": namespace,
        "device": device,
        "ip_address": ip_address,
    }


def write_netns_config(
    namespace: str,
    device: str,
    ip_address: str,
    netmask: str,
    gateway: str,
    *,
    base_dir: str = "/etc/netns",
) -> Path:
    """Write persistent network config file for a namespace.

    Creates /etc/netns/<namespace>/network/<device> with static IP config.
    This file is used to restore configuration on daemon restart.

    Args:
        namespace: Network namespace name.
        device: Network device name.
        ip_address: IPv4 address.
        netmask: IPv4 netmask.
        gateway: IPv4 gateway.
        base_dir: Base directory for netns configs (injectable for testing).

    Returns:
        Path to the written config file.

    Raises:
        IOError: If config file cannot be written or verified.
    """
    config_dir = Path(base_dir) / namespace / "network"
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create config directory {config_dir}: {e}")
        raise IOError(f"Cannot create config directory: {e}") from e

    config_path = config_dir / device
    prefix_len = _netmask_to_prefix(netmask)

    config_content = (
        f"# Auto-generated by encryptor-sim daemon\n"
        f"# Namespace: {namespace}\n"
        f"auto {device}\n"
        f"iface {device} inet static\n"
        f"    address {ip_address}/{prefix_len}\n"
        f"    netmask {netmask}\n"
        f"    gateway {gateway}\n"
    )

    try:
        config_path.write_text(config_content)
    except OSError as e:
        logger.error(f"Failed to write config file {config_path}: {e}")
        raise IOError(f"Cannot write config file: {e}") from e

    # Verify the file was written successfully
    if not config_path.exists():
        logger.error(f"Config file does not exist after write: {config_path}")
        raise IOError(f"Config file verification failed: {config_path}")

    # Verify content matches what we wrote
    try:
        written_content = config_path.read_text()
        if written_content != config_content:
            logger.error(f"Config file content mismatch: {config_path}")
            raise IOError(f"Config file content verification failed")
    except OSError as e:
        logger.error(f"Failed to verify config file {config_path}: {e}")
        raise IOError(f"Cannot verify config file: {e}") from e

    logger.info(f"Wrote and verified network config: {config_path}")
    return config_path


def _parse_proc_net_dev(output: str, device: str) -> dict[str, int]:
    """Parse /proc/net/dev output for a specific device.

    Args:
        output: Raw content of /proc/net/dev.
        device: Device name to extract stats for (e.g. "eth1").

    Returns:
        Dict with bytesRx, bytesTx, packetsRx, packetsTx, errorsRx, errorsTx.
    """
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{device}:"):
            # Format: device: rx_bytes rx_packets rx_errs ... tx_bytes tx_packets tx_errs ...
            parts = stripped.split(":", 1)[1].split()
            if len(parts) >= 11:
                return {
                    "bytesRx": int(parts[0]),
                    "packetsRx": int(parts[1]),
                    "errorsRx": int(parts[2]),
                    "bytesTx": int(parts[8]),
                    "packetsTx": int(parts[9]),
                    "errorsTx": int(parts[10]),
                }
    return {
        "bytesRx": 0, "bytesTx": 0,
        "packetsRx": 0, "packetsTx": 0,
        "errorsRx": 0, "errorsTx": 0,
    }


def _zero_stats() -> dict[str, int]:
    """Return zeroed interface stats dict."""
    return {
        "bytesRx": 0, "bytesTx": 0,
        "packetsRx": 0, "packetsTx": 0,
        "errorsRx": 0, "errorsTx": 0,
    }


def get_interface_stats(
    *,
    runner: Runner = subprocess.run,
) -> dict[str, dict[str, int]]:
    """Query interface statistics for CT, PT, MGMT namespaces.

    Reads /proc/net/dev inside each network namespace to get
    bytes, packets, and error counts.

    Args:
        runner: Command runner (injectable for testing).

    Returns:
        Dict mapping interface name to stats dict with keys:
        bytesRx, bytesTx, packetsRx, packetsTx, errorsRx, errorsTx.
    """
    stats: dict[str, dict[str, int]] = {}

    for iface_name, mapping in INTERFACE_MAP.items():
        namespace = mapping["namespace"]
        device = mapping["device"]
        try:
            result = runner(
                ["ip", "netns", "exec", namespace, "cat", "/proc/net/dev"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.error(
                    f"Failed to read stats for {iface_name} in {namespace}: "
                    f"{result.stderr.strip()}"
                )
                stats[iface_name] = _zero_stats()
                continue

            stats[iface_name] = _parse_proc_net_dev(result.stdout, device)

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Cannot read stats for {iface_name}: {e}")
            stats[iface_name] = _zero_stats()

    return stats


def verify_isolation_after_config(
    *,
    runner: Runner = subprocess.run,
) -> dict[str, str]:
    """Verify isolation rules are still in place after configuration.

    Returns:
        Dict with verification status.
    """
    for namespace in ("ns_pt", "ns_ct"):
        result = runner(
            [
                "ip", "netns", "exec", namespace, "nft", "list", "chain",
                "inet", "isolation", "forward",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if getattr(result, "returncode", 0) != 0:
            return {
                "status": "fail",
                "message": f"Isolation rules missing in {namespace}",
            }
        output = getattr(result, "stdout", "") or ""
        if "policy drop" not in output:
            return {
                "status": "fail",
                "message": (
                    f"Isolation forward policy not set to drop in {namespace}"
                ),
            }

    return {"status": "pass", "message": "Isolation rules verified"}


def restore_interface_configs_from_db(
    *,
    runner: Runner = subprocess.run,
    config_base_dir: str = "/etc/netns",
) -> dict[str, list[str]]:
    """Restore interface configurations from database on daemon startup.

    Loads interface configs from the database and applies them to their
    respective namespaces. This ensures configurations persist across reboots.

    Args:
        runner: Command runner (injectable for testing).
        config_base_dir: Base directory for netns config files.

    Returns:
        Dict with 'restored' list of interface names and 'failed' list.
    """
    # Import here to avoid circular dependency
    from backend.app.db.session import create_session_factory
    from backend.app.models.interface import Interface

    restored = []
    failed = []

    try:
        session_factory = create_session_factory()
        session = session_factory()

        try:
            interfaces = session.query(Interface).all()

            for iface in interfaces:
                # Skip unconfigured interfaces
                if not iface.ipAddress:
                    continue

                try:
                    configure_interface(
                        iface.name,
                        iface.ipAddress,
                        iface.netmask,
                        iface.gateway,
                        runner=runner,
                        config_base_dir=config_base_dir,
                    )
                    restored.append(iface.name)
                    logger.info(f"Restored {iface.name} configuration on startup")
                except Exception as e:
                    failed.append(iface.name)
                    logger.error(f"Failed to restore {iface.name}: {e}")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Failed to restore interface configs: {e}")

    return {"restored": restored, "failed": failed}
