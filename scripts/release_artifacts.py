# 사용: python scripts/release_artifacts.py
# Pareto/STL/벤치 결과를 exports/로 모음
from pathlib import Path, zipfile, json

OUT=Path("exports"); OUT.mkdir(parents=True, exist_ok=True)
paths=[]
for p in [Path("data/pareto"), Path("data/geometry"), Path("data/bench")]:
    if p.exists():
        paths += list(p.rglob("*.*"))
(man:=Path("data/manifest.json")).exists() and paths.append(man)
z=OUT/"blueprint_outputs.zip"
with zipfile.ZipFile(z,"w",compression=zipfile.ZIP_DEFLATED) as f:
    for p in paths: f.write(p, arcname=str(p))
print(json.dumps({"zip": str(z), "files": len(paths)}, ensure_ascii=False))
