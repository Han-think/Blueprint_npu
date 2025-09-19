"""Smoke tests for the rocket FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.rocket import app


def test_rocket_health() -> None:
    client = TestClient(app)
    response = client.get("/rocket/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "rocket"

