import argparse

import json

import time

from pathlib import Path

import requests



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["rocket", "pencil"], default="rocket")
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--topk", type=int, default=16)
    ap.add_argument("--method", default="lhs")
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--host", default="http://127.0.0.1:9007")
    args = ap.parse_args()

    url = f"{args.host}/moo/{args.mode}"
    payload = {
        "samples": args.samples,
        "topk": args.topk,
        "method": args.method,
        "generations": args.generations,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()

    Path("data/pareto").mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = Path(f"data/pareto/{args.mode}_{ts}.json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    latest = Path("data/pareto/latest.json")
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"saved": str(path), "count": len(data.get("top", []))}, ensure_ascii=False, indent=2))
