"""Calibrate the rocket surrogate against RocketCEA if available."""
from __future__ import annotations

import argparse
import json
import statistics as stats
from pathlib import Path

from rocket.cea_adapter import isp_rocketcea
from rocket.evaluator import evaluate_batch
from rocket.sampling import sample_lhs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fuel", default="CH4")
    parser.add_argument("--ox", default="LOX")
    parser.add_argument("--mr", type=float, default=3.5)
    args = parser.parse_args()

    designs = sample_lhs(args.samples, seed=args.seed)
    metrics = evaluate_batch(designs)

    ratios = []
    for metric in metrics:
        design = metric["design"]
        ref = isp_rocketcea(
            design["Pc_MPa"],
            design["eps"],
            fuel=args.fuel,
            oxidizer=args.ox,
            MR=args.mr,
        )
        if ref is None:
            print(json.dumps({"error": "rocketcea_not_available"}, ensure_ascii=False))
            raise SystemExit(0)
        pred = float(metric["Isp_s"])
        if pred > 1e-9:
            ratios.append(ref / pred)

    if not ratios:
        print(json.dumps({"error": "no_pairs"}, ensure_ascii=False))
        raise SystemExit(0)

    k_isp = stats.median(ratios)
    calib_path = Path("data/cea_calib.json")
    config: dict[str, float] = {}
    if calib_path.is_file():
        try:
            config = json.loads(calib_path.read_text(encoding="utf-8"))
        except Exception:
            config = {}
    config["isp_scale"] = float(k_isp)
    calib_path.parent.mkdir(parents=True, exist_ok=True)
    calib_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"isp_scale": k_isp, "pairs": len(ratios)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
