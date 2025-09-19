import json
import time
from pathlib import Path

if __name__ == "__main__":
    model_dir = Path("models")
    model_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in model_dir.iterdir():
        if path.is_file():
            entries.append({"name": path.name, "bytes": path.stat().st_size, "mtime": int(path.stat().st_mtime)})
    manifest = {
        "updated": int(time.time()),
        "files": entries,
        "policy": ["OV: surrogate.xml/bin", "ONNX: surrogate.onnx", "NPZ: surrogate.npz"],
    }
    (model_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(entries)}, ensure_ascii=False))
