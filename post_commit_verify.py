from __future__ import annotations

import json
from pathlib import Path

from app.main import app
from blueprint.pipeline import Pipeline
from fastapi.testclient import TestClient

ARTIFACT_DIR = Path("artifacts")
SUMMARY_FILE = ARTIFACT_DIR / "post_commit_summary.json"


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    pipe = Pipeline(fake=True)
    designs = pipe.generate(16)
    predictions = pipe.predict(designs)
    metrics = pipe.evaluate(designs)
    top = pipe.optimize(samples=32, topk=8)

    client = TestClient(app)
    health = client.get("/health", timeout=5).json()

    summary = {
        "counts": {
            "designs": len(designs),
            "predictions": len(predictions),
            "metrics": len(metrics),
            "top": len(top),
        },
        "health": health,
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "summary_file": str(SUMMARY_FILE)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
