from fastapi.testclient import TestClient

from app.moo3 import app


def test_moo3_health():
    client = TestClient(app)
    response = client.get("/moo3/health")
    assert response.status_code == 200
    assert response.json().get("constraints") == "Deb(proxy)"
