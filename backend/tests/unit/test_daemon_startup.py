from typing import Any

import pytest

from backend.daemon.startup import run_startup_tasks


def test_run_startup_tasks_runs_validation_and_persists_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, Any] = {}

    def fake_apply_isolation_rules() -> None:
        recorded["applied"] = True

    def fake_run_isolation_validation() -> dict[str, object]:
        return {"status": "pass", "timestamp": "now"}

    def fake_set_latest_validation_result(result: dict[str, object]) -> None:
        recorded["result"] = result

    monkeypatch.setattr(
        "backend.daemon.startup.apply_isolation_rules", fake_apply_isolation_rules
    )
    monkeypatch.setattr(
        "backend.daemon.startup.run_isolation_validation", fake_run_isolation_validation
    )
    monkeypatch.setattr(
        "backend.daemon.startup.set_latest_validation_result", fake_set_latest_validation_result
    )

    run_startup_tasks()

    assert recorded["applied"] is True
    assert recorded["result"] == {"status": "pass", "timestamp": "now"}
