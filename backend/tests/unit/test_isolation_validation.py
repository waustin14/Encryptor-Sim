from types import SimpleNamespace
import shutil
import subprocess

from backend.daemon.ops.isolation_validation import run_isolation_validation


def _fake_nft_list_output(ifnames: list[str]) -> str:
    """Simulate nft list chain output (nft omits 'meta' keyword in output)."""
    quoted = ", ".join(f'"{n}"' for n in ifnames)
    ifname_set = f"{{ {quoted} }}"
    return (
        "table inet isolation {\n"
        "    chain forward {\n"
        "        type filter hook forward priority 0; policy drop;\n"
        "        ct state established,related accept\n"
        f"        iifname {ifname_set} oifname {ifname_set} accept\n"
        "    }\n"
        "}\n"
    )


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, cmd: list[str], **kwargs: object) -> SimpleNamespace:
        self.calls.append({"cmd": cmd, **kwargs})

        if cmd[:5] == ["ip", "netns", "exec", "iso-val-test-a", "nft"] and cmd[5:8] == [
            "list",
            "table",
            "inet",
        ]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if cmd[:5] == ["ip", "netns", "exec", "iso-val-test-b", "nft"] and cmd[5:8] == [
            "list",
            "table",
            "inet",
        ]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if cmd[:5] == ["ip", "netns", "exec", "iso-val-test-a", "nft"] and cmd[5:9] == [
            "list",
            "chain",
            "inet",
            "isolation",
        ]:
            output = _fake_nft_list_output(["iso-val-test-a", "iso-val-test-b"])
            return SimpleNamespace(returncode=0, stdout=output, stderr="")
        if cmd[:5] == ["ip", "netns", "exec", "iso-val-test-b", "nft"] and cmd[5:9] == [
            "list",
            "chain",
            "inet",
            "isolation",
        ]:
            output = _fake_nft_list_output(["iso-val-test-a", "iso-val-test-b"])
            return SimpleNamespace(returncode=0, stdout=output, stderr="")

        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_run_isolation_validation_success_records_checks_and_cleans_up(monkeypatch: object) -> None:
    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/fake")
    runner = FakeRunner()

    result = run_isolation_validation(runner=runner, name_suffix="test")

    assert result["status"] == "pass"
    assert result["failures"] == []
    assert result["checks"]
    assert all(check["status"] == "pass" for check in result["checks"])
    cleanup_calls = [
        call["cmd"] for call in runner.calls if call["cmd"][:3] == ["ip", "netns", "del"]
    ]
    assert cleanup_calls == [
        ["ip", "netns", "del", "iso-val-test-a"],
        ["ip", "netns", "del", "iso-val-test-b"],
    ]


def test_run_isolation_validation_failure_marks_status_and_attempts_cleanup(monkeypatch: object) -> None:
    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/fake")
    def failing_runner(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        if cmd[:5] == ["ip", "netns", "exec", "iso-val-fail-a", "nft"] and cmd[5:9] == [
            "list",
            "chain",
            "inet",
            "isolation",
        ]:
            if kwargs.get("check"):
                raise subprocess.CalledProcessError(1, cmd, stderr="boom")
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        if kwargs.get("check"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = run_isolation_validation(runner=failing_runner, name_suffix="fail")

    assert result["status"] == "fail"
    assert result["failures"]
