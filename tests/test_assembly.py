"""Smoke test for the assembly FastAPI endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.assembly import app


def test_assembly_health() -> None:
    client = TestClient(app)
    response = client.get("/assembly/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "rocket_assembly" in data["modes"]
