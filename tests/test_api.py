import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.main import app  # noqa: E402


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_generate_predict_evaluate_cycle():
    client = TestClient(app)
    designs = client.post("/generate", json={"count": 4}).json()["designs"]
    scores = client.post("/predict", json={"designs": designs}).json()["y"]
    metrics = client.post("/evaluate", json={"designs": designs}).json()["metrics"]
    assert len(scores) == 4
    assert len(metrics) == 4
    top = client.post("/optimize", json={"samples": 16, "topk": 4}).json()["top"]
    assert len(top) == 4
