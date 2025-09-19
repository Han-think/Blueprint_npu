from __future__ import annotations

from pathlib import Path


def init_db(path: str = "data/experiments/index.db") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("", encoding="utf-8")
    return p
