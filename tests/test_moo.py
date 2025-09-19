from fastapi.testclient import TestClient

from app.moo import app


def test_moo_health():
    client = TestClient(app)
    response = client.get("/moo/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_moo_rocket_endpoint():
    client = TestClient(app)
    response = client.post(
        "/moo/rocket",
        json={"samples": 8, "topk": 4, "seed": 123, "pa_kpa": 90.0},
    )
    assert response.status_code == 200
    assert "top" in response.json()


def test_moo_pencil_endpoint():
    client = TestClient(app)
    response = client.post(
        "/moo/pencil",
        json={"samples": 8, "topk": 4, "seed": 123, "M0": 0.9, "alt_m": 2000.0},
    )
    assert response.status_code == 200
    assert "top" in response.json()
