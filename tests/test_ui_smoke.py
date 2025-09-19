from fastapi.testclient import TestClient

from app.ui import app


def test_ui_health() -> None:
    client = TestClient(app)
    response = client.get("/ui/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
