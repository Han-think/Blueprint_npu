import os
import sys
from importlib import reload
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def _get_client():
    os.environ.setdefault("ALLOW_FAKE_GEN", "1")
    # Reload the module to pick up environment overrides in isolated tests
    from src.api import server

    reload(server)
    return TestClient(server.app)


def test_health_endpoint_reports_ok():
    client = _get_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert "device" in payload


def test_infer_returns_payload():
    client = _get_client()
    resp = client.post("/v1/infer", json={"prompt": "ping", "max_new_tokens": 4})
    assert resp.status_code == 200
    payload = resp.json()
    assert "result" in payload
    assert payload["result"].startswith("[")
