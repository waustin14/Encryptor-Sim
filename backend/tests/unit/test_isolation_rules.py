import shutil
from types import SimpleNamespace
from typing import Any

import pytest

from backend.daemon.ops.nftables import (
    apply_isolation_rules,
    build_default_ns_ruleset,
    build_isolation_ruleset,
    build_pt_ns_ruleset,
)


class TestBuildDefaultNsRuleset:
    """Tests for the default namespace isolation ruleset."""

    def test_allows_xfrm_to_veth(self) -> None:
        ruleset = build_default_ns_ruleset()
        assert 'meta iifname "xfrm*" meta oifname "veth_ct_default" accept' in ruleset

    def test_allows_veth_to_xfrm(self) -> None:
        ruleset = build_default_ns_ruleset()
        assert 'meta iifname "veth_ct_default" meta oifname "xfrm*" accept' in ruleset

    def test_drops_by_default(self) -> None:
        ruleset = build_default_ns_ruleset()
        assert "policy drop" in ruleset

    def test_allows_established(self) -> None:
        ruleset = build_default_ns_ruleset()
        assert "ct state established,related accept" in ruleset


class TestBuildPtNsRuleset:
    """Tests for the ns_pt isolation ruleset."""

    def test_allows_eth2_to_veth_ct_pt(self) -> None:
        ruleset = build_pt_ns_ruleset()
        assert 'meta iifname "eth2" meta oifname "veth_ct_pt" accept' in ruleset

    def test_allows_veth_ct_pt_to_eth2(self) -> None:
        ruleset = build_pt_ns_ruleset()
        assert 'meta iifname "veth_ct_pt" meta oifname "eth2" accept' in ruleset

    def test_drops_by_default(self) -> None:
        ruleset = build_pt_ns_ruleset()
        assert "policy drop" in ruleset

    def test_allows_established(self) -> None:
        ruleset = build_pt_ns_ruleset()
        assert "ct state established,related accept" in ruleset


class TestBuildGenericRuleset:
    """Tests for the generic/custom isolation ruleset."""

    def test_uses_provided_ifnames(self) -> None:
        ruleset = build_isolation_ruleset(["foo", "bar"])
        assert 'meta iifname { "foo", "bar" }' in ruleset
        assert 'meta oifname { "foo", "bar" }' in ruleset

    def test_drops_by_default(self) -> None:
        ruleset = build_isolation_ruleset(["foo"])
        assert "policy drop" in ruleset


class TestApplyIsolationRules:
    """Tests for apply_isolation_rules."""

    def test_defaults_target_default_and_ns_pt(self) -> None:
        if shutil.which("ip") is None or shutil.which("nft") is None:
            pytest.skip("Requires ip and nft commands (linux runtime)")

        calls: list[dict[str, Any]] = []

        def fake_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            calls.append({"cmd": cmd, **kwargs})
            # Simulate table not existing yet
            if cmd[-3:] == ["nft", "list", "table"] or \
               (len(cmd) >= 4 and cmd[-4:] == ["nft", "list", "table", "inet"]):
                return SimpleNamespace(returncode=1)
            return SimpleNamespace(returncode=0)

        apply_isolation_rules(runner=fake_runner)

        # Should have operations for both "default" and "ns_pt"
        # Default namespace: no "ip netns exec" prefix
        default_apply = [
            c for c in calls
            if c["cmd"][:2] == ["nft", "-f"] and c.get("input")
        ]
        nspt_apply = [
            c for c in calls
            if len(c["cmd"]) >= 6
            and c["cmd"][:3] == ["ip", "netns", "exec"]
            and c["cmd"][3] == "ns_pt"
            and "nft" in c["cmd"]
            and "-f" in c["cmd"]
            and c.get("input")
        ]

        assert len(default_apply) == 1, "Expected one nft apply for default namespace"
        assert len(nspt_apply) == 1, "Expected one nft apply for ns_pt"

        # Verify correct rulesets are applied
        assert 'iifname "xfrm*"' in default_apply[0]["input"]
        assert 'iifname "eth2"' in nspt_apply[0]["input"]

    def test_custom_ifnames_use_generic_ruleset(self) -> None:
        if shutil.which("ip") is None or shutil.which("nft") is None:
            pytest.skip("Requires ip and nft commands (linux runtime)")

        calls: list[dict[str, Any]] = []

        def fake_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            calls.append({"cmd": cmd, **kwargs})
            if "list" in cmd:
                return SimpleNamespace(returncode=1)
            return SimpleNamespace(returncode=0)

        apply_isolation_rules(
            namespaces=["ns_pt", "ns_ct"],
            allowed_ifnames=["pt", "ct"],
            runner=fake_runner,
        )

        apply_calls = [c for c in calls if c.get("input")]

        assert [c["cmd"][3] for c in apply_calls] == ["ns_pt", "ns_ct"]
        assert all('meta iifname { "pt", "ct" }' in c["input"] for c in apply_calls)

    def test_ns_mgmt_filtered_from_defaults(self) -> None:
        """ns_mgmt is not in DEFAULT_NAMESPACES so it never gets rules by default."""
        if shutil.which("ip") is None or shutil.which("nft") is None:
            pytest.skip("Requires ip and nft commands (linux runtime)")

        calls: list[dict[str, Any]] = []

        def fake_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
            calls.append({"cmd": cmd, **kwargs})
            if "list" in cmd:
                return SimpleNamespace(returncode=1)
            return SimpleNamespace(returncode=0)

        # Default invocation (no explicit namespaces) — ns_mgmt not targeted
        apply_isolation_rules(runner=fake_runner)

        # Should only target "default" and "ns_pt"
        apply_calls = [c for c in calls if c.get("input")]
        namespaces_targeted = []
        for c in apply_calls:
            cmd = c["cmd"]
            if cmd[:3] == ["ip", "netns", "exec"]:
                namespaces_targeted.append(cmd[3])
            elif cmd[:2] == ["nft", "-f"]:
                namespaces_targeted.append("default")
        assert "ns_mgmt" not in namespaces_targeted
        assert "default" in namespaces_targeted
        assert "ns_pt" in namespaces_targeted
