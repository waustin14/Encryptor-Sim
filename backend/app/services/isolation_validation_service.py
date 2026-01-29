from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.isolation_validation import IsolationValidationResult
from backend.app.ws.system_events import emit_isolation_status_updated


def _coerce_timestamp(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def record_validation_result(
    session: Session,
    result: dict[str, object],
) -> IsolationValidationResult:
    record = IsolationValidationResult(
        status=str(result.get("status", "unknown")),
        timestamp=_coerce_timestamp(result["timestamp"]),
        checks=list(result.get("checks", [])),
        failures=list(result.get("failures", [])),
        durationSeconds=float(result.get("duration", 0.0)),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    emit_isolation_status_updated(
        {
            "status": record.status,
            "timestamp": record.timestamp.isoformat(),
            "checks": record.checks,
            "failures": record.failures,
            "duration": record.durationSeconds,
        }
    )
    return record


def get_latest_validation_result(session: Session) -> IsolationValidationResult | None:
    stmt = (
        select(IsolationValidationResult)
        .order_by(IsolationValidationResult.timestamp.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()
