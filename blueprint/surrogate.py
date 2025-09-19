from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None) -> None:
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
        self._compiled = None
        if not fake:
            self._try_load_openvino()

    def _try_load_openvino(self) -> None:
        xml = Path("models/surrogate.xml")
        bin_path = Path("models/surrogate.bin")
        if not (xml.exists() and bin_path.exists()):
            self._compiled = None
            self.device_selected = "CPU"
            return
        try:
            from openvino.runtime import Core  # type: ignore[import-untyped]

            core = Core()
            preference = ["NPU", "GPU", "CPU"]
            if self.device_hint and self.device_hint in preference:
                preference = [self.device_hint] + [d for d in preference if d != self.device_hint]
            chosen = next((dev for dev in preference if dev in core.available_devices), "CPU")
            self._compiled = core.compile_model(model=str(xml), device_name=chosen)
            self.device_selected = chosen
        except Exception:  # pragma: no cover - OpenVINO optional
            self._compiled = None
            self.device_selected = "CPU"

    def predict(self, designs: list[list[float]]) -> list[float]:
        array = np.asarray(designs, dtype=float)
        if self.fake or self._compiled is None:
            return (1.0 - np.sum(array * array, axis=1)).tolist()
        try:
            result = self._compiled([array.astype(np.float32)])[self._compiled.outputs[0]]
            return np.asarray(result).ravel().astype(float).tolist()
        except Exception:  # pragma: no cover - inference fallback
            return (1.0 - np.sum(array * array, axis=1)).tolist()
