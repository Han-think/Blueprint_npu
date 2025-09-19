from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np


class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
        self.compiled = None
        if not fake:
            self._try_load_openvino()

    def _try_load_openvino(self) -> None:
        xml = Path("models/surrogate.xml")
        bin_file = Path("models/surrogate.bin")
        if not (xml.exists() and bin_file.exists()):
            self.compiled = None
            self.device_selected = "CPU"
            return
        try:
            from openvino.runtime import Core

            core = Core()
            preferred = [d for d in (self.device_hint, "NPU", "GPU", "CPU") if d]
            chosen = next((d for d in preferred if d in core.available_devices), "CPU")
            model = core.read_model(model=str(xml))
            self.compiled = core.compile_model(model=model, device_name=chosen)
            self.device_selected = chosen
        except Exception:
            self.compiled = None
            self.device_selected = "CPU"

    def predict(self, designs: List[List[float]]) -> List[float]:
        x = np.asarray(designs, dtype=float)
        if self.fake or self.compiled is None:
            y = 1.0 - np.sum(x * x, axis=1)
            return y.tolist()
        try:
            result = self.compiled([x.astype(np.float32)])[self.compiled.outputs[0]]
            return np.asarray(result).ravel().astype(float).tolist()
        except Exception:
            y = 1.0 - np.sum(x * x, axis=1)
            return y.tolist()
