from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.proof_api import app


def test_proof_demo_creates_artifacts(monkeypatch):
    monkeypatch.setenv("BLUEPRINT_FAKE", "1")
    client = TestClient(app)
    response = client.post(
        "/proof/run_demo",
        json={"mode": "base", "samples": 32, "topk": 4, "noise": 0.01},
    )
    assert response.status_code == 200
    payload = response.json()
    run_dir = Path(payload["dir"])  # directory is absolute or relative to repo
    assert run_dir.exists()

    expected_files = {
        "designs.jsonl",
        "predictions.jsonl",
        "measurements.jsonl",
        "designs.csv",
        "predictions.csv",
        "measurements.csv",
        "run_meta.json",
    }
    assert expected_files.issubset({p.name for p in run_dir.iterdir()})
    assert payload["summary"]["rmse"] >= 0.0 or payload["summary"]["rmse"] != payload["summary"]["rmse"]

    shutil.rmtree(run_dir)
