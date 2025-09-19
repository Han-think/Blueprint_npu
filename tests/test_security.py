"""Ensure optional API key protection behaves as expected."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.mission import app


def test_security_optional() -> None:
    os.environ.pop("API_KEY", None)
    client = TestClient(app)
    response = client.post(
        "/mission/fighter",
        json={"M0": 0.9, "alt_m": 2_000, "legs": [{"type": "cruise", "M": 0.9, "dt_s": 60}]},
    )
    assert response.status_code == 200


def test_security_key_required() -> None:
    os.environ["API_KEY"] = "secret"
    client = TestClient(app)
    response = client.post(
        "/mission/fighter",
        json={"M0": 0.9, "alt_m": 2_000, "legs": [{"type": "cruise", "M": 0.9, "dt_s": 60}]},
    )
    assert response.status_code == 401
    response = client.post(
        "/mission/fighter",
        headers={"x-api-key": "secret"},
        json={"M0": 0.9, "alt_m": 2_000, "legs": [{"type": "cruise", "M": 0.9, "dt_s": 60}]},
    )
    assert response.status_code == 200
    os.environ.pop("API_KEY", None)
