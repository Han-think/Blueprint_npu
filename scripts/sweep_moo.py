"""Batch sweep helper for the constraint-aware MOO service."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import requests


def _hash_payload(url: str, payload: dict[str, object]) -> str:
    digest = hashlib.sha256()
    digest.update(url.encode())
    digest.update(json.dumps(payload, sort_keys=True).encode())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["rocket", "pencil"], default="rocket")
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--gens", type=int, default=12)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--host", default="http://127.0.0.1:9019")
    args = parser.parse_args()

    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, int]] = []
    for seed in range(args.seeds):
        payload = {"samples": args.samples, "generations": args.gens, "seed": seed}
        url = f"{args.host}/moo3/{args.mode}"
        cache_key = _hash_payload(url, payload)
        cache_path = cache_dir / f"{cache_key}.json"
        if cache_path.is_file():
            result = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append({"seed": seed, "count": len(result.get("top", []))})

    summary_path = cache_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(summary)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
