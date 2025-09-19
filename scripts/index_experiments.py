"""Index proof experiment runs into a lightweight SQLite database."""

from __future__ import annotations

from pathlib import Path

from proof.index_db import init_db, upsert_run


def main() -> None:
    init_db()
    root = Path("data/experiments")
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        meta = entry / "run_meta.json"
        if meta.is_file():
            upsert_run(str(meta))
    print("indexed")


if __name__ == "__main__":
    main()
