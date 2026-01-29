import shutil
from types import SimpleNamespace
from typing import Any

import pytest

from backend.daemon.ops.nftables import apply_isolation_rules, build_isolation_ruleset


def test_build_isolation_ruleset_includes_required_allow_rules() -> None:
    ruleset = build_isolation_ruleset()

    assert 'meta iifname { "pt", "ct" } meta oifname { "pt", "ct" }' in ruleset
    assert "udp dport { 500, 4500 } accept" in ruleset
    assert "ip protocol esp accept" in ruleset
    assert "policy drop" in ruleset


def test_apply_isolation_rules_only_targets_pt_ct() -> None:
    if shutil.which("ip") is None or shutil.which("nft") is None:
        pytest.skip("Requires ip and nft commands (linux runtime)")

    calls: list[dict[str, Any]] = []

    def fake_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append({"cmd": cmd, **kwargs})
        if cmd[4:7] == ["nft", "list", "table"]:
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)

    apply_isolation_rules(
        namespaces=["ns_pt", "ns_ct", "ns_mgmt"],
        allowed_ifnames=["pt", "ct"],
        runner=fake_runner,
    )

    list_calls = [call for call in calls if call["cmd"][4:7] == ["nft", "list", "table"]]
    add_calls = [call for call in calls if call["cmd"][4:7] == ["nft", "add", "table"]]
    apply_calls = [call for call in calls if call["cmd"][4:6] == ["nft", "-f"]]

    assert [call["cmd"][3] for call in list_calls] == ["ns_pt", "ns_ct"]
    assert [call["cmd"][3] for call in add_calls] == ["ns_pt", "ns_ct"]
    assert [call["cmd"][3] for call in apply_calls] == ["ns_pt", "ns_ct"]
    assert all('meta iifname { "pt", "ct" }' in call["input"] for call in apply_calls)
