"""Train a simple polynomial surrogate for the base pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from blueprint.pipeline import Pipeline


def poly_features(X: np.ndarray, degree: int) -> np.ndarray:
    n, d = X.shape
    feats = [np.ones((n, 1)), X]
    if degree >= 2:
        feats.append(X ** 2)
        for i in range(d):
            for j in range(i + 1, d):
                feats.append((X[:, i : i + 1] * X[:, j : j + 1]))
    if degree >= 3:
        feats.append(X ** 3)
    return np.hstack(feats)


def train_on_random(samples: int, degree: int) -> dict:
    pipeline = Pipeline(fake=False)
    X = np.asarray(pipeline.generate(samples), dtype=float)
    y = np.asarray(pipeline.predict(X.tolist()), dtype=float)
    Phi = poly_features(X, degree)
    weights, *_ = np.linalg.lstsq(Phi, y, rcond=None)
    return {"w": weights, "deg": degree}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="base", choices=["base"])
    parser.add_argument("--samples", type=int, default=2048)
    parser.add_argument("--poly", type=int, default=2)
    parser.add_argument("--out", default="models/surrogate.npz")
    args = parser.parse_args()

    model = train_on_random(samples=args.samples, degree=args.poly)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, **model)
    print(json.dumps({"saved": args.out, "deg": int(model["deg"]), "w_len": int(model["w"].shape[0])}, indent=2))


if __name__ == "__main__":
    main()
