"""Seed a synthetic CEA reference table used for calibration demos."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/cea/cea_table.csv")
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Pc_MPa", "eps", "Isp_s"])
        rows = 0
        for Pc in [3, 5, 7, 10, 12, 15]:
            for eps in [6, 10, 15, 20, 25, 30, 35, 40]:
                isp = 180 + 20 * math.log(Pc) + 3.5 * (eps ** 0.35)
                writer.writerow([Pc, eps, round(isp, 2)])
                rows += 1

    print({"seeded": str(output), "rows": rows})


if __name__ == "__main__":
    main()

