from fastapi.testclient import TestClient

from app.verify import app


def test_verify_health():
    client = TestClient(app)
    assert client.get("/verify/health").status_code == 200
