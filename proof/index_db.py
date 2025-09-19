 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

from pathlib import Path


def init_db(path: str = "data/experiments/index.db") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("", encoding="utf-8")
    return p

"""SQLite helpers for indexing experiment outputs."""

from __future__ import annotations

import json

import sqlite3

from pathlib import Path


def init_db(db_path: str = "data/experiments/index.db") -> None:
    """Initialise the experiments index database if needed."""

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS runs(" "run_id TEXT PRIMARY KEY, mode TEXT, samples INT, topk INT, noise REAL)"
        )
        cur.execute("CREATE TABLE IF NOT EXISTS files(run_id TEXT, kind TEXT, path TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS summary(run_id TEXT, rmse REAL, corr REAL)")
        con.commit()
    finally:
        con.close()


def upsert_run(meta_path: str, db_path: str = "data/experiments/index.db") -> None:
    """Insert or update the runs table using metadata from the proof logger."""

    with open(meta_path, "r", encoding="utf-8") as handle:
        meta = json.load(handle)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO runs(run_id, mode, samples, topk, noise) VALUES(?,?,?,?,?)",
            (
                meta.get("run_id"),
                meta.get("mode"),
                meta.get("samples"),
                meta.get("topk"),
                meta.get("noise"),
            ),
        )
        con.commit()
    finally:
        con.close()
 main
