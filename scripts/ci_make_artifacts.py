"""Create sample Pareto and STL artifacts for smoke checks."""

from __future__ import annotations

import json
from pathlib import Path


def _write_sample_stl(path: Path) -> None:
    path.write_text(
        """solid nozzle
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 1 0 0
      vertex 1 1 0
      vertex 0 1 0
    endloop
  endfacet
endsolid nozzle
""",
        encoding="utf-8",
    )


def main() -> None:
    base = Path(".").resolve()
    pareto_dir = base / "data" / "pareto"
    geometry_dir = base / "data" / "geometry"
    pareto_dir.mkdir(parents=True, exist_ok=True)
    geometry_dir.mkdir(parents=True, exist_ok=True)

    pareto_data = {
        "top": [
            {
                "design": {
                    "Pc_MPa": 10.0,
                    "rt_mm": 20.0,
                    "eps": 20.0,
                    "gamma": 1.2,
                    "Tc_K": 3200.0,
                    "R": 340.0,
                },
                "score": 1.0,
            }
        ]
    }
    (pareto_dir / "latest.json").write_text(
        json.dumps(pareto_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _write_sample_stl(geometry_dir / "nozzle_top.stl")


if __name__ == "__main__":
    main()
