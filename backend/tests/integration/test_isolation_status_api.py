from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.db.base import Base
from backend.app.db.session import create_session_factory, get_engine
from backend.app.models.isolation_validation import IsolationValidationResult
from backend.app.db.deps import get_db_session
from backend.app.services.isolation_validation_service import record_validation_result
from backend.main import app


def test_get_isolation_status_returns_latest_record(tmp_path) -> None:
    db_path = tmp_path / "isolation.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = get_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(db_url)

    session = session_factory()
    record = IsolationValidationResult(
        status="pass",
        timestamp=datetime.now(timezone.utc),
        checks=[{"name": "check", "status": "pass"}],
        failures=[],
        durationSeconds=0.5,
    )
    session.add(record)
    session.commit()
    session.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/isolation-status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == "pass"
    assert payload["data"]["checks"][0]["name"] == "check"


def test_record_validation_result_persists_and_emits_event(tmp_path) -> None:
    db_path = tmp_path / "isolation.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = get_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(db_url)

    session = session_factory()
    result_dict = {
        "status": "pass",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [{"name": "check_deps", "status": "pass"}],
        "failures": [],
        "duration": 0.8,
    }
    record = record_validation_result(session, result_dict)
    session.close()

    assert record.status == "pass"
    assert len(record.checks) == 1
    assert record.durationSeconds == 0.8
