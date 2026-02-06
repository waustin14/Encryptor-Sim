from backend.daemon.ops.isolation_validation import (
    run_isolation_validation,
    set_latest_validation_result,
)
from backend.daemon.ops.network_ops import restore_interface_configs_from_db
from backend.daemon.ops.nftables import apply_isolation_rules


def run_startup_tasks() -> None:
    apply_isolation_rules()
    restore_interface_configs_from_db()
    result = run_isolation_validation()
    set_latest_validation_result(result)
