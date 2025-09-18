from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_generate_predict_evaluate() -> None:
    client = TestClient(app)
    designs = client.post("/generate", json={"count": 4}).json()["designs"]
    preds = client.post("/predict", json={"designs": designs}).json()["y"]
    metrics = client.post("/evaluate", json={"designs": designs}).json()["metrics"]
    assert len(preds) == 4
    assert len(metrics) == 4
