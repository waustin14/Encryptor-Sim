"""Interface configuration API endpoints.

Provides endpoints for viewing and configuring CT, PT, and MGMT interfaces.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_user
from backend.app.db.deps import get_db_session
from backend.app.models.user import User
from backend.app.schemas.interface import (
    InterfaceConfigEnvelope,
    InterfaceConfigRequest,
    InterfaceConfigResponse,
    InterfaceListEnvelope,
)
from backend.app.services.daemon_ipc import send_command
from backend.app.services.interface_service import (
    get_all_interfaces,
    get_interface_by_name,
    rollback_interface_config,
    update_interface_config,
    validate_interface_config,
)
from backend.app.utils.rfc7807 import create_rfc7807_error
from backend.app.ws.monitoring import get_monitoring_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interfaces", tags=["interfaces"])


async def _broadcast_interface_config_change(action: str, interface_name: str) -> None:
    """Best-effort WebSocket broadcast for interface config changes."""
    try:
        manager = get_monitoring_ws_manager()
        await manager.broadcast(
            {
                "type": "interface.config_changed",
                "data": {"action": action, "interface": interface_name},
            }
        )
    except Exception as e:
        logger.warning("Failed to broadcast interface config change: %s", e)


@router.get("", response_model=InterfaceListEnvelope)
def list_interfaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> InterfaceListEnvelope:
    """List all interface configurations.

    Returns CT, PT, and MGMT interface configurations.
    """
    interfaces = get_all_interfaces(db)
    data = [InterfaceConfigResponse.model_validate(iface) for iface in interfaces]
    return InterfaceListEnvelope(data=data, meta={"count": len(data)})


@router.get("/{name}", response_model=InterfaceConfigEnvelope)
def get_interface(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> InterfaceConfigEnvelope:
    """Get a specific interface configuration by name (CT, PT, or MGMT)."""
    interface = get_interface_by_name(db, name)
    if interface is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Interface '{name.upper()}' not found",
                instance=f"/api/v1/interfaces/{name}",
            ),
        )
    data = InterfaceConfigResponse.model_validate(interface)
    return InterfaceConfigEnvelope(data=data, meta={})


@router.post("/{name}/configure", response_model=InterfaceConfigEnvelope)
async def configure_interface(
    name: str,
    config: InterfaceConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> InterfaceConfigEnvelope:
    """Configure an interface's IP settings.

    Sets IP address, netmask, and gateway for the specified interface.
    """
    # Validate the configuration
    is_valid, error_msg = validate_interface_config(
        config.ipAddress, config.netmask, config.gateway
    )
    if not is_valid:
        raise HTTPException(
            status_code=422,
            detail=create_rfc7807_error(
                status=422,
                title="Validation Error",
                detail=error_msg,
                instance=f"/api/v1/interfaces/{name}/configure",
            ),
        )

    # Find the interface
    interface = get_interface_by_name(db, name)
    if interface is None:
        raise HTTPException(
            status_code=404,
            detail=create_rfc7807_error(
                status=404,
                title="Not Found",
                detail=f"Interface '{name.upper()}' not found",
                instance=f"/api/v1/interfaces/{name}/configure",
            ),
        )

    # Preserve previous values so we can restore on isolation failure.
    prev_ip = interface.ipAddress
    prev_netmask = interface.netmask
    prev_gateway = interface.gateway

    # Update the configuration in the database first
    updated = update_interface_config(
        db, interface, config.ipAddress, config.netmask, config.gateway
    )

    # Apply configuration via daemon IPC (best-effort)
    daemon_applied = False
    daemon_available = True
    try:
        response = send_command(
            "configure_interface",
            {
                "namespace": interface.namespace,
                "device": interface.device,
                "ip_address": config.ipAddress,
                "netmask": config.netmask,
                "gateway": config.gateway,
            },
        )
        result = response.get("result", {})
        daemon_status = result.get("status")
        daemon_applied = daemon_status == "success"

        # Check for isolation failures (critical error)
        isolation = result.get("isolation", {})
        if isolation.get("status") == "fail":
            # Isolation failure is critical - restore prior DB values and fail.
            rollback_interface_config(db, interface, prev_ip, prev_netmask, prev_gateway)
            raise HTTPException(
                status_code=500,
                detail=create_rfc7807_error(
                    status=500,
                    title="Internal Server Error",
                    detail=f"Isolation check failed: {isolation.get('message')}",
                    instance=f"/api/v1/interfaces/{name}/configure",
                ),
            )
    except (ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        # Daemon unavailable - log warning but allow DB-only update
        # This is intentional for dev/test environments without daemon
        daemon_available = False
        logger.warning(
            f"Daemon not available for interface {name} configuration: {e}. "
            f"Configuration saved to database only."
        )

    meta = {
        "applied": daemon_applied,
        "daemonAvailable": daemon_available,
    }
    if not daemon_available and not daemon_applied:
        meta["warning"] = "Configuration saved to database only (daemon unavailable)"

    data = InterfaceConfigResponse.model_validate(updated)
    await _broadcast_interface_config_change("updated", name)
    return InterfaceConfigEnvelope(data=data, meta=meta)
