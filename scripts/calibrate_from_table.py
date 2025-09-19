"""Calibrate the rocket Isp scale factor against a reference CEA table."""
from __future__ import annotations

import argparse
import json

from rocket.cea_bridge import fit_isp_scale, update_calib_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="data/cea_table.csv")
    parser.add_argument("--samples", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    scale = fit_isp_scale(n_samples=args.samples, seed=args.seed, table_path=args.table)
    cfg = update_calib_json(scale, path="data/cea_calib.json")
    print(json.dumps({"isp_scale": scale, "cfg": cfg}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
