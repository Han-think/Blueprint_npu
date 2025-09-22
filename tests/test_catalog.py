"""Smoke tests for the catalog API."""

from fastapi.testclient import TestClient

from app.catalog import app


def test_catalog_health_and_keys() -> None:
    client = TestClient(app)

    health_res = client.get("/catalog/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    keys_res = client.get("/catalog/keys")
    assert keys_res.status_code == 200
    payload = keys_res.json()
    assert "rocket" in payload and "pencil" in payload
    assert isinstance(payload["rocket"], list) and isinstance(payload["pencil"], list)

