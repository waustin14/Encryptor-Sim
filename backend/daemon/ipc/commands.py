from collections.abc import Mapping
from typing import Any

from backend.daemon.ops.isolation_validation import get_latest_validation_result
from backend.daemon.ops.network_ops import (
    configure_interface,
    get_interface_stats,
    verify_isolation_after_config,
)
from backend.daemon.ops.nftables import apply_isolation_rules
from backend.daemon.ops.strongswan_ops import (
    configure_peer,
    get_tunnel_status,
    get_tunnel_telemetry,
    initiate_peer,
    reload_peer_config,
    remove_peer_config,
    teardown_peer,
    write_routes_config,
)


class CommandError(ValueError):
    pass


def handle_command(command: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if command == "enforce_isolation":
        namespaces = None
        allowed_ifnames = None
        if payload and "namespaces" in payload:
            namespaces = list(payload["namespaces"])
        if payload and "allowedIfnames" in payload:
            allowed_ifnames = list(payload["allowedIfnames"])
        elif payload and "allowed_ifnames" in payload:
            allowed_ifnames = list(payload["allowed_ifnames"])
        apply_isolation_rules(namespaces=namespaces, allowed_ifnames=allowed_ifnames)
        return {"applied": True}

    if command == "get_validation_result":
        return get_latest_validation_result()

    if command == "configure_interface":
        if not payload:
            raise CommandError("configure_interface requires payload")
        required = ("namespace", "device", "ip_address", "netmask", "gateway")
        missing = [k for k in required if k not in payload]
        if missing:
            raise CommandError(f"Missing required fields: {', '.join(missing)}")

        # Map namespace back to interface name for validation
        ns_to_name = {"ns_ct": "CT", "ns_pt": "PT", "ns_mgmt": "MGMT"}
        name = ns_to_name.get(payload["namespace"])
        if name is None:
            raise CommandError(f"Unknown namespace: {payload['namespace']}")

        result = configure_interface(
            name,
            payload["ip_address"],
            payload["netmask"],
            payload["gateway"],
        )

        # Verify isolation is maintained after configuration
        isolation = verify_isolation_after_config()
        result["isolation"] = isolation

        return result

    if command == "configure_peer":
        if not payload:
            raise CommandError("configure_peer requires payload")
        required = ("name", "remote_ip", "psk", "ike_version")
        missing = [k for k in required if k not in payload]
        if missing:
            raise CommandError(f"Missing required fields: {', '.join(missing)}")

        result = configure_peer(
            name=payload["name"],
            remote_ip=payload["remote_ip"],
            psk=payload["psk"],
            ike_version=payload["ike_version"],
            dpd_action=payload.get("dpd_action", "restart"),
            dpd_delay=payload.get("dpd_delay", 30),
            dpd_timeout=payload.get("dpd_timeout", 150),
            rekey_time=payload.get("rekey_time", 3600),
        )
        return result

    if command == "initiate_peer":
        if not payload:
            raise CommandError("initiate_peer requires payload")
        if "name" not in payload:
            raise CommandError("Missing required field: name")

        return initiate_peer(name=payload["name"])

    if command == "teardown_peer":
        if not payload:
            raise CommandError("teardown_peer requires payload")
        if "name" not in payload:
            raise CommandError("Missing required field: name")

        return teardown_peer(name=payload["name"])

    if command == "remove_peer_config":
        if not payload:
            raise CommandError("remove_peer_config requires payload")
        if "name" not in payload:
            raise CommandError("Missing required field: name")

        return remove_peer_config(name=payload["name"])

    if command == "update_routes":
        if not payload:
            raise CommandError("update_routes requires payload")
        required = ("peer_name", "routes")
        missing = [k for k in required if k not in payload]
        if missing:
            raise CommandError(f"Missing required fields: {', '.join(missing)}")

        result = write_routes_config(
            name=payload["peer_name"],
            routes=list(payload["routes"]),
        )

        # Reload connections to apply route changes
        reload_result = reload_peer_config(name=payload["peer_name"])
        result["reload"] = reload_result.get("message", "")

        return result

    if command == "get_tunnel_status":
        return get_tunnel_status()

    if command == "get_tunnel_telemetry":
        return get_tunnel_telemetry()

    if command == "get_interface_stats":
        return get_interface_stats()

    raise CommandError(f"Unknown command: {command}")
