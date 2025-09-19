from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict


class JsonlWriter:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("w", encoding="utf-8")

    def write(self, obj: Dict[str, Any]):
        self._file.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def close(self):
        self._file.close()


def jsonl_to_csv(jsonl_path: Path, csv_path: Path, field_order=None):
    rows = []
    if not jsonl_path.is_file():
        csv_path.write_text("", encoding="utf-8")
        return
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        csv_path.write_text("", encoding="utf-8")
        return
    keys = field_order or sorted({key for row in rows for key in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
