"""Approximate CFD post-processing for Pareto results."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def nozzle_perf(
    rt_mm: float,
    eps: float,
    gamma: float,
    tc_k: float,
    gas_constant: float,
    chamber_pressure_mpa: float,
) -> tuple[float, float, float, float]:
    """Return crude estimates of mass flow, exhaust velocity, thrust, and Isp."""

    pc = chamber_pressure_mpa * 1.0e6
    throat_area = math.pi * (rt_mm * 1.0e-3) ** 2
    mdot = pc * throat_area / 1500.0
    ve = math.sqrt(
        2 * gamma / (gamma - 1.0)
        * gas_constant
        * tc_k
        * (1.0 - (1.0 / eps) ** ((gamma - 1.0) / gamma))
    )
    thrust = mdot * ve + (pc - 101_325.0) * throat_area * (eps - 1.0)
    isp = thrust / (mdot * 9.80665)
    return mdot, ve, thrust, isp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pareto", default="data/pareto/latest.json")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument(
        "--out", default="data/experiments/cfd.csv", help="Destination CSV file"
    )
    args = parser.parse_args()

    pareto = json.loads(Path(args.pareto).read_text(encoding="utf-8"))
    entry = pareto["top"][args.index]
    design = entry.get("design", entry)

    mdot, ve, thrust, isp = nozzle_perf(
        design["rt_mm"],
        design["eps"],
        design["gamma"],
        design["Tc_K"],
        design["R"],
        design["Pc_MPa"],
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["mdot_kg_s", "Ve_m_s", "F_N", "Isp_s"])
        writer.writerow([round(mdot, 3), round(ve, 1), round(thrust, 1), round(isp, 2)])
    print({"csv": str(out_path)})


if __name__ == "__main__":
    main()
