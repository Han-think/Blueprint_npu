from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Mapping


def init_db(db_path: str = "data/experiments/index.db") -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, payload TEXT)"
        )


def upsert_run(run_id: str, payload: Mapping[str, object], db_path: str = "data/experiments/index.db") -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs(run_id, payload) VALUES (?, ?)",
            (run_id, str(dict(payload))),
        )
