import argparse
import csv
import math
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/cea/cea_table.csv")
    args = parser.parse_args()

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Pc_MPa", "eps", "Isp_s"])
        for pc in [3, 5, 7, 10, 12, 15]:
            for eps in [6, 10, 15, 20, 25, 30, 35, 40]:
                isp = 180 + 20 * math.log(pc) + 3.5 * eps ** 0.35
                writer.writerow([pc, eps, round(isp, 2)])
    print({"seeded": str(path), "rows": 6 * 8})
