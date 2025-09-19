"""Latency profiler for deployed Blueprint services."""

from __future__ import annotations

import argparse
import statistics as stats
import time

import requests


def _measure(url: str, attempts: int = 10) -> dict[str, float | bool]:
    durations = []
    status_ok = True
    for _ in range(attempts):
        start = time.perf_counter()
        response = requests.get(url, timeout=10)
        durations.append((time.perf_counter() - start) * 1000.0)
        status_ok = status_ok and response.status_code == 200
    durations.sort()
    return {
        "p50_ms": round(stats.median(durations), 2),
        "p90_ms": round(durations[int(max(len(durations) * 0.9 - 1, 0))], 2),
        "ok": status_ok,
    }


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1")
    parser.add_argument("--ports", nargs="+", type=int, default=[9007])
    args = parser.parse_args()

    for port in args.ports:
        target = f"{args.host.rstrip('/')}" f":{port}/moo/health"
        stats_summary = _measure(target)
        stats_summary.update({"port": port})
        print(stats_summary)

