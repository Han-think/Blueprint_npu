 codex/initialize-npu-inference-template-v1n7c2
import os


codex/initialize-npu-inference-template-ys4nnv
 main
import sys

from pathlib import Path

from fastapi.testclient import TestClient

 codex/initialize-npu-inference-template-v1n7c2
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

sys.path.append(str(Path(__file__).resolve().parents[1]))


import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
main
from app.main import app

def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"

def test_generate_predict_evaluate():
    c = TestClient(app)
    X = c.post("/generate", json={"count": 4}).json()["designs"]
    y = c.post("/predict", json={"designs": X}).json()["y"]
    m = c.post("/evaluate", json={"designs": X}).json()["metrics"]
    assert len(y) == 4 and len(m) == 4
 main
