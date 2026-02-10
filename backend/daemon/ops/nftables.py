from collections.abc import Iterable, Callable
import shutil
import subprocess

# Namespaces that receive isolation rules during normal operation.
# "default" is the init namespace where xfrm* <-> veth_ct_default forwarding
# happens.  "ns_pt" forwards between eth2 (PT hosts) and veth_ct_pt (to
# default namespace).  ns_ct has no forwarding and needs no rules.
DEFAULT_NAMESPACES = ("default", "ns_pt")

# Legacy constant kept for callers that pass explicit allowed_ifnames
# (e.g. isolation_validation.py with temporary test namespaces).
DEFAULT_ISOLATION_IFNAMES = ("eth2", "veth_ct_pt", "veth_ct_default")

# Which namespace names are accepted by apply_isolation_rules.
ISOLATION_NAMESPACES = {"ns_pt", "ns_ct", "default"}


def _check_required_commands() -> None:
    for cmd in ("ip", "nft"):
        if shutil.which(cmd) is None:
            raise RuntimeError(f"Required command not found: {cmd}")


def _format_ifname_set(ifnames: Iterable[str]) -> str:
    unique = tuple(dict.fromkeys(ifnames))
    if not unique:
        raise ValueError("Isolation allowlist requires at least one interface name")
    joined = ", ".join(f'"{name}"' for name in unique)
    return f"{{ {joined} }}"


def build_isolation_ruleset(allowed_ifnames: Iterable[str] | None = None) -> str:
    """Build a generic isolation ruleset for custom/test namespaces.

    Used by isolation_validation and IPC commands that supply explicit
    interface names.  For production defaults use build_default_ns_ruleset()
    or build_pt_ns_ruleset().
    """
    ifname_set = _format_ifname_set(allowed_ifnames or DEFAULT_ISOLATION_IFNAMES)
    return f"""
flush table inet isolation

add chain inet isolation forward {{ type filter hook forward priority 0; policy drop; }}
add rule inet isolation forward ct state established,related accept
add rule inet isolation forward meta iifname {ifname_set} meta oifname {ifname_set} accept
""".lstrip()


def build_default_ns_ruleset() -> str:
    """Build isolation rules for the default (init) namespace.

    The default namespace forwards tunnel traffic between veth_ct_default
    (connected to ns_pt) and xfrm* interfaces (IPsec encryption/decryption).
    All other forwarding is dropped.
    """
    return """\
flush table inet isolation

add chain inet isolation forward { type filter hook forward priority 0; policy drop; }
add rule inet isolation forward ct state established,related accept
add rule inet isolation forward meta iifname "xfrm*" meta oifname "veth_ct_default" accept
add rule inet isolation forward meta iifname "veth_ct_default" meta oifname "xfrm*" accept
"""


def build_pt_ns_ruleset() -> str:
    """Build isolation rules for ns_pt.

    ns_pt forwards plaintext traffic between eth2 (PT hosts) and veth_ct_pt
    (veth endpoint to the default namespace).  All other forwarding is dropped.
    """
    return """\
flush table inet isolation

add chain inet isolation forward { type filter hook forward priority 0; policy drop; }
add rule inet isolation forward ct state established,related accept
add rule inet isolation forward meta iifname "eth2" meta oifname "veth_ct_pt" accept
add rule inet isolation forward meta iifname "veth_ct_pt" meta oifname "eth2" accept
"""


def _ruleset_for_namespace(
    namespace: str,
    allowed_ifnames: Iterable[str] | None = None,
) -> str:
    """Return the correct ruleset for a namespace.

    When allowed_ifnames is provided (custom/test usage), the generic ruleset
    is used.  Otherwise namespace-specific production rulesets are returned.
    """
    if allowed_ifnames is not None:
        return build_isolation_ruleset(allowed_ifnames)
    if namespace == "default":
        return build_default_ns_ruleset()
    if namespace == "ns_pt":
        return build_pt_ns_ruleset()
    # Fallback for any other namespace (e.g. test namespaces)
    return build_isolation_ruleset()


def _nft_cmd_prefix(namespace: str) -> list[str]:
    """Return the command prefix to run nft in the given namespace."""
    if namespace == "default":
        return []
    return ["ip", "netns", "exec", namespace]


def apply_isolation_rules(
    *,
    namespaces: Iterable[str] | None = None,
    allowed_ifnames: Iterable[str] | None = None,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    _check_required_commands()
    # When allowed_ifnames is provided the caller is doing custom/test
    # isolation (e.g. isolation_validation with temporary namespaces), so
    # accept all listed namespaces.  Otherwise filter against the known
    # production set to prevent accidental rule application to ns_mgmt etc.
    if allowed_ifnames is not None:
        targets = tuple(namespaces or DEFAULT_NAMESPACES)
    else:
        targets = tuple(
            ns for ns in (namespaces or DEFAULT_NAMESPACES)
            if ns in ISOLATION_NAMESPACES
        )

    for namespace in targets:
        ruleset = _ruleset_for_namespace(namespace, allowed_ifnames)
        prefix = _nft_cmd_prefix(namespace)

        result = runner(
            [*prefix, "nft", "list", "table", "inet", "isolation"],
            capture_output=True,
            text=True,
            check=False,
        )
        if getattr(result, "returncode", 0) != 0:
            runner(
                [*prefix, "nft", "add", "table", "inet", "isolation"],
                check=True,
            )
        runner(
            [*prefix, "nft", "-f", "-"],
            input=ruleset,
            text=True,
            check=True,
        )
