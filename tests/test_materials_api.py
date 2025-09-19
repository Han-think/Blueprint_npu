"""Smoke tests for material APIs and combined verification endpoint."""

from fastapi.testclient import TestClient

from app.materials import app as materials_app
from app.verify_material import app as verify_material_app


def test_materials_list() -> None:
    client = TestClient(materials_app)
    assert client.get("/materials/health").status_code == 200
    resp = client.get("/materials/list")
    assert resp.status_code == 200
    assert "keys" in resp.json()


def test_verify_material_health() -> None:
    client = TestClient(verify_material_app)
    assert client.get("/verifym/health").status_code == 200
