"""Train an XGBoost/RandomForest surrogate and export to ONNX or NPZ."""
from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path
from typing import Tuple

import numpy as np


def make_teacher_data(n: int, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    from blueprint.pipeline import Pipeline

    pipeline = Pipeline(fake=False)
    rng_state = np.random.get_state()
    np.random.seed(seed)
    designs = np.asarray(pipeline.generate(n), dtype=float)
    np.random.set_state(rng_state)
    targets = np.asarray(pipeline.predict(designs.tolist()), dtype=float)
    return designs, targets


def train_model(X: np.ndarray, y: np.ndarray):
    model = None
    kind = "rf"
    try:
        from xgboost import XGBRegressor

        model = XGBRegressor(
            n_estimators=400,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            learning_rate=0.05,
            n_jobs=0,
        )
        model.fit(X, y)
        kind = "xgb"
    except Exception:
        model = None

    if model is None:
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(
            n_estimators=400,
            max_depth=None,
            n_jobs=0,
            random_state=0,
        )
        model.fit(X, y)
        kind = "rf"
    return model, kind


def export_onnx(model, X_sample: np.ndarray, out_path: Path) -> bool:
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType

        n_features = X_sample.shape[1]
        onnx_model = convert_sklearn(
            model,
            initial_types=[("input", FloatTensorType([None, n_features]))],
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(onnx_model.SerializeToString())
        return True
    except Exception:
        return False


def save_npz(X: np.ndarray, y: np.ndarray, out_path: Path) -> Path:
    Phi = np.c_[np.ones((len(X), 1)), X, X ** 2]
    weights, *_ = np.linalg.lstsq(Phi, y, rcond=None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, w=weights, deg=2)
    return out_path


def update_manifest() -> None:
    try:
        runpy.run_module("scripts.update_manifest", run_name="__main__")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="models/surrogate.onnx")
    args = parser.parse_args()

    X, y = make_teacher_data(args.samples, args.seed)
    model, kind = train_model(X, y)
    onnx_path = Path(args.out)
    exported = export_onnx(model, X[:2], onnx_path)

    if not exported:
        npz_path = Path("models/surrogate.npz")
        save_npz(X, y, npz_path)
        out_file = str(npz_path)
    else:
        out_file = str(onnx_path)

    update_manifest()
    print(
        json.dumps(
            {"trained": kind, "onnx_saved": exported, "out": out_file},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
