from collections.abc import Iterable, Callable
import shutil
import subprocess

DEFAULT_NAMESPACES = ("ns_pt", "ns_ct")
DEFAULT_ISOLATION_IFNAMES = ("pt", "ct")
ISOLATION_NAMESPACES = {"ns_pt", "ns_ct"}


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
    ifname_set = _format_ifname_set(allowed_ifnames or DEFAULT_ISOLATION_IFNAMES)
    return f"""
flush table inet isolation

add chain inet isolation forward {{ type filter hook forward priority 0; policy drop; }}
add rule inet isolation forward ct state established,related meta iifname {ifname_set} meta oifname {ifname_set} accept
add rule inet isolation forward meta iifname {ifname_set} meta oifname {ifname_set} udp dport {{ 500, 4500 }} accept
add rule inet isolation forward meta iifname {ifname_set} meta oifname {ifname_set} ip protocol esp accept
""".lstrip()


def apply_isolation_rules(
    *,
    namespaces: Iterable[str] | None = None,
    allowed_ifnames: Iterable[str] | None = None,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    _check_required_commands()
    ruleset = build_isolation_ruleset(allowed_ifnames)
    targets = tuple(ns for ns in (namespaces or DEFAULT_NAMESPACES) if ns in ISOLATION_NAMESPACES)

    for namespace in targets:
        result = runner(
            ["ip", "netns", "exec", namespace, "nft", "list", "table", "inet", "isolation"],
            capture_output=True,
            text=True,
            check=False,
        )
        if getattr(result, "returncode", 0) != 0:
            runner(
                ["ip", "netns", "exec", namespace, "nft", "add", "table", "inet", "isolation"],
                check=True,
            )
        runner(
            ["ip", "netns", "exec", namespace, "nft", "-f", "-"],
            input=ruleset,
            text=True,
            check=True,
        )
