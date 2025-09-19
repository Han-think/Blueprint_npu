from fastapi.testclient import TestClient

from app.meta import app


def test_meta_health_and_units():
    client = TestClient(app)
    assert client.get("/meta/health").status_code == 200
    assert client.get("/meta/units").status_code == 200
