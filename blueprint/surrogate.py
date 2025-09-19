from __future__ import annotations
import numpy as np
from pathlib import Path
from typing import Optional

class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
        self.compiled = None
        self.lin_model = False
        self._lin_w: Optional[np.ndarray] = None
        self._lin_deg: int = 1
        if not fake:
            self._try_load_openvino()
        self._load_npz_fallback()

    def _try_load_openvino(self):
        xml = Path("models/surrogate.xml")
        binf = Path("models/surrogate.bin")
        if not (xml.exists() and binf.exists()):
            self.compiled = None
            self.device_selected = "CPU"
            return
        try:
            from openvino.runtime import Core
            core = Core()
            pref = ["NPU","GPU","CPU"]
            if self.device_hint and self.device_hint in pref:
                pref = [self.device_hint] + [d for d in pref if d != self.device_hint]
            chosen = next((d for d in pref if d in core.available_devices), "CPU")
            self.compiled = core.compile_model(model=str(xml), device_name=chosen)
            self.device_selected = chosen
        except Exception:
            self.compiled = None
            self.device_selected = "CPU"

    def _load_npz_fallback(self) -> None:
        if self.fake or self.compiled is not None:
            return
        npz_path = Path("models/surrogate.npz")
        if not npz_path.exists():
            return
        try:
            data = np.load(npz_path)
            self._lin_w = data["w"]
            self._lin_deg = int(data["deg"])
            self.lin_model = True
            self.device_selected = "NPZ"
        except Exception:
            self.lin_model = False
            self._lin_w = None
            self._lin_deg = 1

    def _poly_features(self, X: np.ndarray) -> np.ndarray:
        n, d = X.shape
        feats = [np.ones((n, 1)), X]
        if self._lin_deg >= 2:
            feats.append(X ** 2)
            for i in range(d):
                for j in range(i + 1, d):
                    feats.append(X[:, i : i + 1] * X[:, j : j + 1])
        if self._lin_deg >= 3:
            feats.append(X ** 3)
        return np.hstack(feats)

    def predict(self, designs: list[list[float]]) -> list[float]:
        X = np.asarray(designs, dtype=float)
        if self.lin_model and self._lin_w is not None:
            Phi = self._poly_features(X)
            y = Phi.dot(self._lin_w)
            return np.asarray(y).ravel().astype(float).tolist()
        if self.fake or self.compiled is None:
            y = 1.0 - np.sum(X * X, axis=1)  # 더미: -||x||^2 + 1
            return y.tolist()
        try:
            res = self.compiled([X.astype(np.float32)])[self.compiled.outputs[0]]
            return np.asarray(res).ravel().astype(float).tolist()
        except Exception:
            y = 1.0 - np.sum(X * X, axis=1)
            return y.tolist()
