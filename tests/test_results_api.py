from fastapi.testclient import TestClient

from app.results import app


def test_results_health():
    client = TestClient(app)
    response = client.get("/results/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
