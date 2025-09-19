from fastapi.testclient import TestClient

from app.metrics2 import app


def test_metrics2_serves() -> None:
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "bp_requests_total" in response.text
