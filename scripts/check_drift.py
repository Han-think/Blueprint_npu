import argparse
import json
import math
import statistics as stats
from pathlib import Path


def population_stability_index(expected, actual, bins=10):
    if not expected or not actual:
        return None
    lo = min(min(expected), min(actual))
    hi = max(max(expected), max(actual))
    if hi <= lo:
        hi = lo + 1.0
    step = (hi - lo) / bins
    expected_counts = [0] * bins
    actual_counts = [0] * bins
    for value in expected:
        idx = min(bins - 1, int((value - lo) / step))
        expected_counts[idx] += 1
    for value in actual:
        idx = min(bins - 1, int((value - lo) / step))
        actual_counts[idx] += 1
    psi = 0.0
    for e_count, a_count in zip(expected_counts, actual_counts):
        e = max(e_count / len(expected), 1e-6)
        a = max(a_count / len(actual), 1e-6)
        psi += (a - e) * math.log(a / e)
    return psi


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="data/experiments/measurements.jsonl")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(json.dumps({"error": "file_not_found", "path": str(path)}, ensure_ascii=False))
        raise SystemExit(0)

    expected = []
    actual = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
            pred = payload.get("pred", {})
            meas = payload.get("meas", {})
            for key in ("Isp_s", "F_N", "score"):
                if key in pred and key in meas:
                    expected.append(float(pred[key]))
                    actual.append(float(meas[key]))
                    break
        except Exception:
            continue

    if not expected:
        print(json.dumps({"error": "no_pairs"}, ensure_ascii=False))
        raise SystemExit(0)

    rmse = math.sqrt(stats.mean([(a - b) ** 2 for a, b in zip(actual, expected)]))
    psi = population_stability_index(expected, actual) or 0.0
    print(json.dumps({"pairs": len(expected), "rmse": rmse, "psi": psi}, ensure_ascii=False, indent=2))
