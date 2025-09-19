"""Update the models manifest with the current directory contents."""

from __future__ import annotations

import json
import time
from pathlib import Path


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    models_dir = Path("models")
    models_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for item in models_dir.iterdir():
        if item.is_file():
            files.append(
                {
                    "name": item.name,
                    "bytes": item.stat().st_size,
                    "mtime": int(item.stat().st_mtime),
                }
            )

    manifest = {
        "updated": int(time.time()),
        "files": files,
        "policy": ["OV: surrogate.xml/bin", "ONNX: surrogate.onnx", "NPZ: surrogate.npz"],
    }
    out_path = models_dir / "manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(files)}, ensure_ascii=False, indent=2))

