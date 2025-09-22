"""Smoke tests for the geometry API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.geometry import app


def test_geometry_health() -> None:
    client = TestClient(app)
    response = client.get("/geom/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_geometry_nozzle_profile_json() -> None:
    client = TestClient(app)
    response = client.get(
        "/geom/rocket/nozzle",
        params={"rt_mm": 20.0, "eps": 25.0, "spike_deg": 10.0, "as_stl": 0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] > 0
    assert len(payload["profile"]) == payload["count"]
