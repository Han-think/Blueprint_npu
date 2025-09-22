from fastapi.testclient import TestClient

from app.moo import app


def test_moo_health():
    client = TestClient(app)
    response = client.get("/moo/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
