"""Export top Pareto rocket geometries to STL files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from geometry.rocket_geom import nozzle_profile, revolve_to_triangles
from geometry.export_stl import write_ascii_stl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pareto", required=True)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise SystemExit("no items in pareto")

    out_dir = Path("data/geometry") / Path(args.pareto).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    limit = min(args.top, len(items))
    outputs: list[str] = []
    for idx in range(limit):
        design = items[idx].get("design") or {}
        rt_mm = float(design.get("rt_mm", 20.0))
        eps = float(design.get("eps", 20.0))
        spike_deg = float(design.get("spike_deg", 10.0))
        profile = nozzle_profile(rt_mm * 1e-3, eps, spike_deg, n=120)
        triangles = revolve_to_triangles(profile, seg=96)
        path = out_dir / f"nozzle_{idx}.stl"
        write_ascii_stl(str(path), f"nozzle_{idx}", triangles)
        outputs.append(str(path))
    print(json.dumps({"exported": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
