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
        if not fake:
            self._try_load_openvino()

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

    def predict(self, designs: list[list[float]]) -> list[float]:
        X = np.asarray(designs, dtype=float)
        if self.fake or self.compiled is None:
            y = 1.0 - np.sum(X * X, axis=1)  # 더미: -||x||^2 + 1
            return y.tolist()
        try:
            res = self.compiled([X.astype(np.float32)])[self.compiled.outputs[0]]
            return np.asarray(res).ravel().astype(float).tolist()
        except Exception:
            y = 1.0 - np.sum(X * X, axis=1)
            return y.tolist()
