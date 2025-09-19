import argparse
import json
from pathlib import Path

from geometry.export_stl import write_ascii_stl
from geometry.rocket_geom import nozzle_profile, revolve_to_triangles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pareto", required=True)
    parser.add_argument("--out", default="nozzle_top.stl")
    parser.add_argument("--seg", type=int, default=96)
    args = parser.parse_args()

    data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise SystemExit("no items in pareto")
    design = items[0].get("design") or {}
    rt_mm = float(design.get("rt_mm", 20.0))
    eps = float(design.get("eps", 20.0))
    spike_deg = float(design.get("spike_deg", 10.0))
    profile = nozzle_profile(rt_mm * 1e-3, eps, spike_deg, n=120)
    triangles = revolve_to_triangles(profile, seg=args.seg)
    write_ascii_stl(args.out, "nozzle_top", triangles)
    print(json.dumps({"out": args.out, "rt_mm": rt_mm, "eps": eps, "spike_deg": spike_deg}, ensure_ascii=False, indent=2))
