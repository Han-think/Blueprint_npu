from fastapi.testclient import TestClient

from app.aggregate import app


def test_aggregate_health():
    client = TestClient(app)
    response = client.get("/aggregate/health")
    assert response.status_code == 200
