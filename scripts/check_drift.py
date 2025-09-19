"""Simple drift checker for experiment measurement logs."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def _psi(expected: list[float], actual: list[float], bins: int = 10) -> float | None:
    if not expected or not actual:
        return None

    low = min(min(expected), min(actual))
    high = max(max(expected), max(actual))
    if high <= low:
        high = low + 1.0
    step = (high - low) / bins

    expected_counts = [0] * bins
    actual_counts = [0] * bins

    for value in expected:
        index = min(bins - 1, int((value - low) / step))
        expected_counts[index] += 1
    for value in actual:
        index = min(bins - 1, int((value - low) / step))
        actual_counts[index] += 1

    psi = 0.0
    for exp_count, act_count in zip(expected_counts, actual_counts):
        exp_freq = max(exp_count / len(expected), 1e-6)
        act_freq = max(act_count / len(actual), 1e-6)
        psi += (act_freq - exp_freq) * math.log(act_freq / exp_freq)
    return psi


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        default="data/experiments/measurements.jsonl",
        help="Path to the measurements JSONL file.",
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(json.dumps({"error": "file_not_found", "path": str(path)}))
        raise SystemExit(0)

    expected: list[float] = []
    actual: list[float] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        prediction = payload.get("pred", {})
        measurement = payload.get("meas", {})
        for key in ("Isp_s", "F_N", "score"):
            if key in prediction and key in measurement:
                expected.append(float(prediction[key]))
                actual.append(float(measurement[key]))
                break

    if not expected:
        print(json.dumps({"error": "no_pairs"}))
        raise SystemExit(0)

    rmse = math.sqrt(
        statistics.mean((a - b) * (a - b) for a, b in zip(actual, expected))
    )
    psi_value = _psi(expected, actual) or 0.0
    print(
        json.dumps(
            {"pairs": len(expected), "rmse": rmse, "psi": psi_value},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
