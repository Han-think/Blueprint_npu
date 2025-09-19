from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path("data/experiments")
    runs = []
    if root.is_dir():
        for meta in root.glob("**/run_meta.json"):
            try:
                runs.append(json.loads(meta.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    print(json.dumps({"runs_indexed": len(runs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
