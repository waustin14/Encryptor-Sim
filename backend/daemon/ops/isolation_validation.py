from collections.abc import Callable, Iterable
from datetime import datetime, timezone
import shutil
import subprocess
import time
import uuid

from backend.daemon.ops.nftables import apply_isolation_rules

Runner = Callable[..., subprocess.CompletedProcess]

_latest_result: dict[str, object] | None = None


def set_latest_validation_result(result: dict[str, object]) -> None:
    global _latest_result
    _latest_result = dict(result)


def get_latest_validation_result() -> dict[str, object] | None:
    return dict(_latest_result) if _latest_result is not None else None


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


def _run_command(runner: Runner, cmd: list[str], *, check: bool = True, **kwargs: object) -> subprocess.CompletedProcess:
    result = runner(cmd, check=check, **kwargs)
    if getattr(result, "returncode", 0) != 0 and check:
        raise subprocess.CalledProcessError(result.returncode, cmd, stderr=getattr(result, "stderr", None))
    return result


def _build_temp_names(name_suffix: str | None) -> tuple[str, str, str, str]:
    suffix = name_suffix or uuid.uuid4().hex[:5]
    namespace_a = f"iso-val-{suffix}-a"
    namespace_b = f"iso-val-{suffix}-b"
    return namespace_a, namespace_b, namespace_a, namespace_b


def _create_namespaces(runner: Runner, namespace_a: str, namespace_b: str) -> None:
    _run_command(runner, ["ip", "netns", "add", namespace_a])
    _run_command(runner, ["ip", "netns", "add", namespace_b])


def _create_veth_pair(runner: Runner, namespace_a: str, namespace_b: str, veth_a: str, veth_b: str) -> None:
    _run_command(runner, ["ip", "link", "add", veth_a, "type", "veth", "peer", "name", veth_b])
    _run_command(runner, ["ip", "link", "set", veth_a, "netns", namespace_a])
    _run_command(runner, ["ip", "link", "set", veth_b, "netns", namespace_b])


def _bring_interfaces_up(runner: Runner, namespace: str, veth: str, ip_address: str) -> None:
    _run_command(runner, ["ip", "netns", "exec", namespace, "ip", "link", "set", "lo", "up"])
    _run_command(runner, ["ip", "netns", "exec", namespace, "ip", "link", "set", veth, "up"])
    _run_command(runner, ["ip", "netns", "exec", namespace, "ip", "addr", "add", ip_address, "dev", veth])


def _verify_ruleset(runner: Runner, namespace: str, allowed_ifnames: Iterable[str]) -> None:
    ifname_set = _format_ifname_set(allowed_ifnames)
    # nft list output omits the "meta" keyword for well-known expressions
    # like iifname/oifname, so match against the output format (no "meta").
    expected_fragments = (
        f"iifname {ifname_set} oifname {ifname_set}",
        "policy drop",
    )
    result = _run_command(
        runner,
        ["ip", "netns", "exec", namespace, "nft", "list", "chain", "inet", "isolation", "forward"],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    missing = [fragment for fragment in expected_fragments if fragment not in output]
    if missing:
        raise RuntimeError(f"Isolation ruleset validation failed: missing {missing}")


def _cleanup_namespaces(runner: Runner, namespaces: Iterable[str]) -> list[str]:
    cleanup_errors: list[str] = []
    for namespace in namespaces:
        try:
            _run_command(runner, ["ip", "netns", "del", namespace], check=False)
        except Exception as exc:
            cleanup_errors.append(f"{namespace}: {exc}")
    return cleanup_errors


def run_isolation_validation(
    *,
    runner: Runner = subprocess.run,
    name_suffix: str | None = None,
) -> dict[str, object]:
    start = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()
    checks: list[dict[str, str]] = []
    failures: list[str] = []
    status = "pass"
    namespace_a, namespace_b, veth_a, veth_b = _build_temp_names(name_suffix)

    def record_check(name: str, action: Callable[[], None]) -> None:
        nonlocal status
        try:
            action()
        except Exception as exc:  # pragma: no cover - exercised via tests with failures
            status = "fail"
            message = f"{name}: {exc}"
            failures.append(message)
            checks.append({"name": name, "status": "fail", "details": str(exc)})
            raise
        else:
            checks.append({"name": name, "status": "pass"})

    try:
        record_check("check_dependencies", _check_required_commands)
        record_check("create_namespaces", lambda: _create_namespaces(runner, namespace_a, namespace_b))
        record_check("create_veth_pair", lambda: _create_veth_pair(runner, namespace_a, namespace_b, veth_a, veth_b))
        record_check(
            "bring_interfaces_up",
            lambda: (
                _bring_interfaces_up(runner, namespace_a, veth_a, "169.254.100.1/30"),
                _bring_interfaces_up(runner, namespace_b, veth_b, "169.254.100.2/30"),
            ),
        )
        record_check(
            "apply_isolation_rules",
            lambda: apply_isolation_rules(
                namespaces=[namespace_a, namespace_b],
                allowed_ifnames=[veth_a, veth_b],
                runner=runner,
            ),
        )
        record_check(
            "verify_ruleset",
            lambda: (
                _verify_ruleset(runner, namespace_a, [veth_a, veth_b]),
                _verify_ruleset(runner, namespace_b, [veth_a, veth_b]),
            ),
        )
    except Exception:
        pass
    finally:
        cleanup_errors = _cleanup_namespaces(runner, [namespace_a, namespace_b])
        if cleanup_errors:
            status = "fail"
            failures.extend([f"cleanup: {error}" for error in cleanup_errors])
            checks.append({"name": "cleanup", "status": "fail", "details": "; ".join(cleanup_errors)})
        else:
            checks.append({"name": "cleanup", "status": "pass"})

    duration = time.monotonic() - start
    return {
        "status": status,
        "timestamp": timestamp,
        "checks": checks,
        "failures": failures,
        "duration": duration,
    }
