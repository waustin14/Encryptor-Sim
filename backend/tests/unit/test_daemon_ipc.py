from typing import Any

import pytest

from backend.daemon.ipc.commands import CommandError, handle_command


def test_handle_command_enforce_isolation_calls_ops(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, Any] = {}

    def fake_apply_isolation_rules(
        *,
        namespaces: list[str] | None = None,
        allowed_ifnames: list[str] | None = None,
    ) -> None:
        recorded["namespaces"] = namespaces
        recorded["allowed_ifnames"] = allowed_ifnames

    monkeypatch.setattr(
        "backend.daemon.ipc.commands.apply_isolation_rules", fake_apply_isolation_rules
    )

    result = handle_command(
        "enforce_isolation",
        {"namespaces": ["ns_pt", "ns_ct"], "allowedIfnames": ["pt", "ct"]},
    )

    assert recorded["namespaces"] == ["ns_pt", "ns_ct"]
    assert recorded["allowed_ifnames"] == ["pt", "ct"]
    assert result == {"applied": True}


def test_handle_command_unknown_raises() -> None:
    with pytest.raises(CommandError):
        handle_command("unknown", {})


def test_handle_command_get_validation_result_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = {"status": "pass", "timestamp": "2026-01-25T12:00:00Z"}

    monkeypatch.setattr(
        "backend.daemon.ipc.commands.get_latest_validation_result", lambda: fake_result
    )

    result = handle_command("get_validation_result")

    assert result == fake_result


def test_handle_command_get_validation_result_returns_none_when_no_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.daemon.ipc.commands.get_latest_validation_result", lambda: None
    )

    result = handle_command("get_validation_result")

    assert result is None
