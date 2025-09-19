 codex/initialize-npu-inference-template-v1n7c2

"""Index proof experiment runs into a lightweight SQLite database."""

 main
from __future__ import annotations

from pathlib import Path

 codex/initialize-npu-inference-template-v1n7c2

def main() -> None:
    root = Path("data/experiments")
    root.mkdir(parents=True, exist_ok=True)
    print({"indexed": 0, "root": str(root)})

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
 main


if __name__ == "__main__":
    main()
