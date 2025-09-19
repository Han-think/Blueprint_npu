"""Filter Pareto results by material constraints and optional cost limit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rocket.material_check import evaluate_material


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pareto", required=True, help="Path to Pareto JSON file")
    parser.add_argument("--material", default="Inconel718")
    parser.add_argument("--max_cost", type=float, default=1e9)
    args = parser.parse_args()

    data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    filtered = []
    for item in data.get("top", []):
        design = item.get("design") or {}
        report = evaluate_material(design, item, material=args.material)
        if report["thermal_ok"] and report["cost_usd"] <= args.max_cost:
            filtered.append({"design": design, "metric": item, "material": report})

    out_path = Path("data/pareto/filtered.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"items": filtered}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"kept": len(filtered)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
