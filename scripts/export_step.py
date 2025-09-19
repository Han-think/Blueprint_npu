"""Export a STEP model for a Pareto design entry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from geometry.step_export import export_step_nozzle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pareto", required=True)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--out", default="nozzle.step")
    args = parser.parse_args()

    data = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    items = data.get("top", [])
    if not items:
        raise SystemExit("no items in pareto")

    idx = max(0, min(args.index, len(items) - 1))
    design = items[idx].get("design") or {}
    rt = float(design.get("rt_mm", 20.0)) * 1e-3
    eps = float(design.get("eps", 20.0))
    spike = float(design.get("spike_deg", 10.0))

    try:
        step_path = export_step_nozzle(args.out, rt, eps, spike)
        print(json.dumps({"step": step_path}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
