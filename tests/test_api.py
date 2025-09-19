from fastapi.testclient import TestClient

from src.api.server import app


def test_health():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body


def test_infer_fake():
    client = TestClient(app)
    res = client.post("/v1/infer", json={"prompt": "ping", "max_new_tokens": 4})
    assert res.status_code == 200
    body = res.json()
    assert "result" in body
    assert "elapsed_ms" in body
