"""Export SHA-256 manifest for generated Pareto and geometry artifacts."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

BASE = Path(".").resolve()
GEO = BASE / "data" / "geometry"
PAR = BASE / "data" / "pareto"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    GEO.mkdir(parents=True, exist_ok=True)
    PAR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {"ts": int(time.time()), "stl": [], "pareto": []}

    stl_entries: list[dict[str, object]] = []
    for path in sorted(GEO.glob("*.stl")):
        data = path.read_bytes()
        stl_entries.append(
            {"name": path.name, "bytes": len(data), "sha256": _sha256(data)}
        )
    manifest["stl"] = stl_entries

    pareto_entries: list[dict[str, object]] = []
    for path in sorted(PAR.glob("*.json")):
        data = path.read_bytes()
        pareto_entries.append(
            {"name": path.name, "bytes": len(data), "sha256": _sha256(data)}
        )
    manifest["pareto"] = pareto_entries

    out_path = BASE / "data" / "manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "files": len(stl_entries) + len(pareto_entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
