from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Optional

import numpy as np


class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
        self.compiled = None
        self._output = None
        if not fake:
            self._try_load_openvino()

    def _try_load_openvino(self) -> None:
        xml = Path("models/surrogate.xml")
        bin_file = Path("models/surrogate.bin")
        if not (xml.exists() and bin_file.exists()):
            self.compiled = None
            self.device_selected = "CPU"
            return
        if importlib.util.find_spec("openvino.runtime") is None:
            self.compiled = None
            self.device_selected = "CPU"
            return
        from openvino.runtime import Core

        core = Core()
        preferred = ["NPU", "GPU", "CPU"]
        if self.device_hint and self.device_hint in preferred:
            preferred = [self.device_hint] + [d for d in preferred if d != self.device_hint]
        chosen = next((d for d in preferred if d in core.available_devices), "CPU")
        try:
            model = core.read_model(model=str(xml), weights=str(bin_file))
            compiled = core.compile_model(model=model, device_name=chosen)
        except Exception:
            self.compiled = None
            self.device_selected = "CPU"
            return
        self.compiled = compiled
        self._output = compiled.outputs[0]
        self.device_selected = chosen

    def predict(self, designs: list[list[float]]) -> list[float]:
        x = np.asarray(designs, dtype=float)
        if x.ndim != 2:
            x = np.atleast_2d(x)
        if self.fake or self.compiled is None or self._output is None:
            y = 1.0 - np.sum(x * x, axis=1)
            return y.tolist()
        try:
            inputs = [x.astype(np.float32)]
            result = self.compiled(inputs)[self._output]
            return np.asarray(result).ravel().astype(float).tolist()
        except Exception:
            y = 1.0 - np.sum(x * x, axis=1)
            return y.tolist()
