"""CLI helper that triggers the proof API demo run."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger the proof demo run via HTTP")
    parser.add_argument("--mode", default="rocket", choices=["rocket", "base"], help="Pipeline mode")
    parser.add_argument("--samples", type=int, default=256, help="Number of samples to consider")
    parser.add_argument("--topk", type=int, default=16, help="Number of candidates to keep")
    parser.add_argument("--noise", type=float, default=0.03, help="Relative noise applied to measurements")
    parser.add_argument("--port", type=int, default=9003, help="API port")
    args = parser.parse_args()

    payload: Dict[str, Any] = {
        "mode": args.mode,
        "samples": args.samples,
        "topk": args.topk,
        "noise": args.noise,
    }
    url = f"http://127.0.0.1:{args.port}/proof/run_demo"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
