"""Smoke test for the NSGA-II optimisation service."""
from fastapi.testclient import TestClient

from app.moo2 import app


def test_moo2_health() -> None:
    client = TestClient(app)
    response = client.get("/moo2/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("algo") == "nsga2"
