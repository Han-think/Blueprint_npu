import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

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
