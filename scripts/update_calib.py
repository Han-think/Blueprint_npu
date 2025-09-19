import argparse
import json
from pathlib import Path

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", type=float, default=None)
    ap.add_argument("--dp", type=float, default=None)
    ap.add_argument("--isp", type=float, default=None)
    ap.add_argument("--path", default="data/cea_calib.json")
    args = ap.parse_args()

    path = Path(args.path)
    cfg = json.loads(path.read_text(encoding="utf-8"))

    if args.q is not None:
        cfg["q_bartz_scale"] = float(args.q)
    if args.dp is not None:
        cfg["dp_regen_scale"] = float(args.dp)
    if args.isp is not None:
        cfg["isp_scale"] = float(args.isp)

    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
