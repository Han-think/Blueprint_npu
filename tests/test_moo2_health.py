from fastapi.testclient import TestClient

from app.moo2 import app


def test_moo2_health():
    client = TestClient(app)
    response = client.get("/moo2/health")
    assert response.status_code == 200
    assert response.json().get("algo") == "nsga2"
