"""Smoke tests for the pencil FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.pencil import app


def test_pencil_health() -> None:
    client = TestClient(app)
    response = client.get("/pencil/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "pencil"
