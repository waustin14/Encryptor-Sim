from collections.abc import Mapping
from typing import Any

from backend.daemon.ops.isolation_validation import get_latest_validation_result
from backend.daemon.ops.nftables import apply_isolation_rules


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
        return {"status": "ok"}

    if command == "get_validation_result":
        result = get_latest_validation_result()
        if result is None:
            return {"status": "ok", "result": None}
        return {"status": "ok", "result": result}

    raise CommandError(f"Unknown command: {command}")
