"""Basic smoke tests for the mission API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.mission import app


def test_mission_health() -> None:
    client = TestClient(app)
    response = client.get("/mission/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
