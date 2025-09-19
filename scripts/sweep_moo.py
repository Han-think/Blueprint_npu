import argparse
import json
import hashlib
from pathlib import Path

import requests


def hash_payload(url: str, payload: dict) -> str:
    digest = hashlib.sha256()
    digest.update(url.encode("utf-8"))
    digest.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rocket", "pencil"], default="rocket")
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--gens", type=int, default=12)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--host", default="http://127.0.0.1:9019")
    args = parser.parse_args()

    Path("data/cache").mkdir(parents=True, exist_ok=True)
    runs = []
    for seed in range(args.seeds):
        payload = {"samples": args.samples, "generations": args.gens, "seed": seed}
        url = f"{args.host}/moo3/{args.mode}"
        cache_key = hash_payload(url, payload)
        cache_path = Path("data/cache") / f"{cache_key}.json"
        if cache_path.is_file():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        runs.append({"seed": seed, "count": len(data.get("top", []))})
    summary_path = Path("data/cache/summary.json")
    summary_path.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(runs), "summary": str(summary_path)}, ensure_ascii=False))
