"""Helpers for writing proof-of-concept experiment logs."""

from __future__ import annotations

import csv

import json

from pathlib import Path
from typing import Any, Dict, Iterable, List


class JsonlWriter:
    """Simple JSONL writer that ensures parent directories exist."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = path.open("w", encoding="utf-8")

    def write(self, obj: Dict[str, Any]) -> None:
        self._file.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def close(self) -> None:
        self._file.close()


def jsonl_to_csv(jsonl_path: Path, csv_path: Path, field_order: Iterable[str] | None = None) -> None:
    """Convert a JSONL file into CSV for quick inspection."""

    rows: List[Dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))

    if not rows:
        csv_path.write_text("", encoding="utf-8")
        return

    keys = list(field_order) if field_order is not None else sorted({key for row in rows for key in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
