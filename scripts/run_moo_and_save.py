import argparse
import json
import time
from pathlib import Path

import requests


def run(mode: str, samples: int, topk: int, method: str, generations: int, host: str) -> dict:
    url = f"{host.rstrip('/')}/moo/{mode}"
    payload = {
        "samples": samples,
        "topk": topk,
        "method": method,
        "generations": generations,
    }
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rocket", "pencil"], default="rocket")
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--topk", type=int, default=16)
    parser.add_argument("--method", choices=["random", "lhs", "ga"], default="lhs")
    parser.add_argument("--generations", type=int, default=10)
    parser.add_argument("--host", default="http://127.0.0.1:9007")
    args = parser.parse_args()

    result = run(args.mode, args.samples, args.topk, args.method, args.generations, args.host)
    Path("data/pareto").mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = Path(f"data/pareto/{args.mode}_{timestamp}.json")
    filename.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    latest = Path("data/pareto/latest.json")
    latest.write_text(filename.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"saved": str(filename), "count": len(result.get("top", []))}, ensure_ascii=False, indent=2))
