from datetime import datetime, timezone
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.errors import not_found
from backend.app.auth.deps import get_current_user
from backend.app.config import BOOT_TARGET_SECONDS, get_boot_duration_seconds
from backend.app.db.deps import get_db_session
from backend.app.models.user import User
from backend.app.schemas.health import (
    HealthData,
    HealthResponse,
    MgmtInterfaceStatus,
    ServiceStatus,
)
from backend.app.schemas.isolation_validation import (
    IsolationStatusResponse,
    IsolationValidationData,
)
from backend.app.services.isolation_validation_service import get_latest_validation_result
from backend.app.services.daemon_ipc import send_command

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/isolation-status", response_model=IsolationStatusResponse)
def get_isolation_status(
    session: Session = Depends(get_db_session),
) -> IsolationStatusResponse:
    record = get_latest_validation_result(session)
    if record is None:
        raise not_found(
            "Isolation validation status not found",
            instance="/api/v1/system/isolation-status",
        )
    data = IsolationValidationData(
        status=record.status,
        timestamp=record.timestamp,
        checks=record.checks,
        failures=record.failures,
        duration=record.durationSeconds,
    )
    return IsolationStatusResponse(data=data, meta={})


def _check_openrc_service_status(service_name: str) -> str:
    """Check OpenRC service status via rc-service."""
    import subprocess

    if shutil.which("rc-service") is None:
        return "unknown"
    try:
        result = subprocess.run(
            ["rc-service", service_name, "status"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return "running" if result.returncode == 0 else "stopped"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception:
        return "unknown"


def _check_namespaces_status() -> str:
    """Check if network namespaces are available."""
    rc_status = _check_openrc_service_status("encryptor-namespaces")
    if rc_status != "unknown":
        return rc_status
    try:
        netns_path = Path("/var/run/netns")
        if not netns_path.exists():
            return "unavailable"
        namespaces = {entry.name for entry in netns_path.iterdir()}
        required = {"ns_ct", "ns_pt", "ns_mgmt"}
        return "running" if required.issubset(namespaces) else "unavailable"
    except Exception:
        return "unknown"


def _check_daemon_status() -> str:
    """Check if daemon IPC socket is available."""
    rc_status = _check_openrc_service_status("encryptor-daemon")
    if rc_status != "unknown":
        return rc_status
    from backend.app.config import get_settings

    socket_path = Path(get_settings().daemon_socket_path)
    if not socket_path.exists():
        return "unavailable"
    try:
        send_command("get_validation_result", timeout=0.5)
        return "running"
    except Exception:
        return "unavailable"


def _check_api_status() -> str:
    """API is running if this endpoint responds."""
    rc_status = _check_openrc_service_status("encryptor-api")
    if rc_status != "unknown":
        return rc_status
    return "running"


def _check_web_ui_status() -> str:
    static_index = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"
    return "running" if static_index.exists() else "unavailable"


def _check_database_status(session: Session) -> str:
    try:
        session.execute(text("SELECT 1"))
        return "running"
    except Exception:
        return "unavailable"


def _check_isolation_status(session: Session) -> str:
    try:
        record = get_latest_validation_result(session)
        if record is None:
            return "unavailable"
        if record.status == "pass":
            return "running"
        return "degraded"
    except Exception:
        return "unknown"


def _cidr_to_netmask(cidr: int) -> str:
    """Convert CIDR notation to dotted netmask."""
    if cidr < 0 or cidr > 32:
        return "255.255.255.0"
    mask = (0xFFFFFFFF >> (32 - cidr)) << (32 - cidr)
    return ".".join(str((mask >> (8 * i)) & 0xFF) for i in range(3, -1, -1))


def _read_network_config_mode() -> str:
    """Read network configuration mode from /etc/encryptor/network-config."""
    config_path = Path("/etc/encryptor/network-config")
    if not config_path.exists():
        return "dhcp"  # Default to DHCP if no config file
    try:
        for line in config_path.read_text().split("\n"):
            line = line.strip()
            if line.startswith("mode="):
                mode = line.split("=", 1)[1].strip()
                if mode in ("static", "dhcp"):
                    return mode
    except Exception:
        pass
    return "dhcp"


def _read_static_config() -> tuple[str | None, str | None]:
    """Read gateway and netmask from static interfaces file."""
    interfaces_path = Path("/etc/network/interfaces.d/mgmt")
    gateway = None
    netmask = None

    if not interfaces_path.exists():
        return gateway, netmask

    try:
        for line in interfaces_path.read_text().split("\n"):
            line = line.strip()
            if line.startswith("gateway"):
                parts = line.split()
                if len(parts) >= 2:
                    gateway = parts[1]
            elif line.startswith("netmask"):
                parts = line.split()
                if len(parts) >= 2:
                    netmask = parts[1]
    except Exception:
        pass

    return gateway, netmask


def _get_mgmt_interface_status() -> MgmtInterfaceStatus:
    """Get MGMT interface IP and DHCP status from ns_mgmt namespace."""
    import subprocess

    interface = "eth0"
    lease_paths = [
        Path("/var/lib/udhcpc/udhcpc.eth0.leases"),
        Path("/var/lib/misc/udhcpc.leases"),
    ]

    try:
        # Check if ns_mgmt namespace exists
        netns_path = Path("/var/run/netns/ns_mgmt")
        if not netns_path.exists():
            return MgmtInterfaceStatus(
                interface=interface,
                ip=None,
                netmask=None,
                gateway=None,
                method="unknown",
                leaseStatus="unknown",
                status="unknown",
            )

        # Get interface IP in ns_mgmt namespace
        result = subprocess.run(
            ["ip", "netns", "exec", "ns_mgmt", "ip", "-4", "addr", "show", interface],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return MgmtInterfaceStatus(
                interface=interface,
                ip=None,
                netmask=None,
                gateway=None,
                method="unknown",
                leaseStatus="unknown",
                status="error",
            )

        # Parse output for IP address and interface state
        ip_addr = None
        netmask = None
        status = "down"

        for line in result.stdout.split("\n"):
            # Check for interface state (UP flag)
            if interface in line and "state UP" in line:
                status = "up"
            elif interface in line and "state DOWN" in line:
                status = "down"

            # Extract IP address and CIDR from inet line
            line = line.strip()
            if line.startswith("inet "):
                parts = line.split()
                if len(parts) >= 2:
                    ip_cidr = parts[1]
                    if "/" in ip_cidr:
                        ip_addr, cidr_str = ip_cidr.split("/")
                        try:
                            netmask = _cidr_to_netmask(int(cidr_str))
                        except ValueError:
                            pass
                    else:
                        ip_addr = ip_cidr

        # Read configuration mode from flag file (Story 2.4)
        config_mode = _read_network_config_mode()

        # Determine effective method based on config and lease files
        method = "static" if config_mode == "static" else "dhcp"
        gateway = None
        has_lease_file = any(path.exists() for path in lease_paths)

        if config_mode == "static":
            # Read gateway from static config file
            gateway, static_netmask = _read_static_config()
            # Prefer netmask from config file if available and not already set
            if static_netmask and not netmask:
                netmask = static_netmask

        if method == "static":
            lease_status = "static"
        elif has_lease_file:
            lease_status = "obtained" if ip_addr else "failed"
        elif ip_addr:
            lease_status = "obtained"
        else:
            lease_status = "failed"

        return MgmtInterfaceStatus(
            interface=interface,
            ip=ip_addr,
            netmask=netmask,
            gateway=gateway,
            method=method,
            leaseStatus=lease_status,
            status=status if ip_addr else "down",
        )

    except subprocess.TimeoutExpired:
        return MgmtInterfaceStatus(
            interface=interface,
            ip=None,
            netmask=None,
            gateway=None,
            method="unknown",
            leaseStatus="unknown",
            status="error",
        )
    except Exception:
        return MgmtInterfaceStatus(
            interface=interface,
            ip=None,
            netmask=None,
            gateway=None,
            method="unknown",
            leaseStatus="unknown",
            status="unknown",
        )


@router.get("/health", response_model=HealthResponse)
def get_health(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> HealthResponse:
    """
    Get system health status including boot duration and service states.

    Returns health data with:
    - status: "healthy" or "degraded"
    - bootDuration: seconds since system boot
    - bootTarget: whether boot duration meets target
    - bootWithinTarget: deprecated alias for bootTarget
    - services: status of namespaces, daemon, and API
    - timestamp: current UTC timestamp
    """
    namespaces_status = _check_namespaces_status()
    daemon_status = _check_daemon_status()
    api_status = _check_api_status()
    web_ui_status = _check_web_ui_status()
    database_status = _check_database_status(session)
    isolation_status = _check_isolation_status(session)

    # Determine overall health (core services only)
    all_running = all(s == "running" for s in [namespaces_status, daemon_status, api_status])
    overall_status = "healthy" if all_running else "degraded"

    services = ServiceStatus(
        namespaces=namespaces_status,
        daemon=daemon_status,
        api=api_status,
        database=database_status,
        isolation=isolation_status,
        webUi=web_ui_status,
    )

    mgmt_interface = _get_mgmt_interface_status()

    boot_duration = get_boot_duration_seconds()
    boot_target = None if boot_duration is None else (boot_duration < BOOT_TARGET_SECONDS)
    boot_within_target = boot_target

    data = HealthData(
        status=overall_status,
        bootDuration=boot_duration,
        bootTarget=boot_target,
        bootTargetSeconds=BOOT_TARGET_SECONDS,
        bootWithinTarget=boot_within_target,
        services=services,
        mgmtInterface=mgmt_interface,
        timestamp=datetime.now(timezone.utc),
    )

    return HealthResponse(data=data, meta={})
