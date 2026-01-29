from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_missing_returns_404() -> None:
    response = client.get("/")

    assert response.status_code == 404
