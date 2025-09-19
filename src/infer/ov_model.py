from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Any


class OVRunner:
    def __init__(self) -> None:
        self.xml = os.environ.get("OV_XML_PATH") or self._auto_find()
        self.device = os.environ.get("OV_DEVICE", "AUTO")
        self.fake = os.environ.get("ALLOW_FAKE_GEN", "1") == "1"
        self._core = None
        self._compiled = None
        if not self.fake and self.xml and Path(self.xml).exists():
            try:
                import openvino as ov

                core = ov.Core()
                self._compiled = core.compile_model(core.read_model(self.xml), self.device)
                self._core = core
            except Exception:
                self.fake = True
        else:
            self.fake = True

    def _auto_find(self) -> str:
        candidates = glob.glob("exports/**/*.xml", recursive=True) + glob.glob(
            "models/**/*.xml", recursive=True
        )
        return candidates[0] if candidates else ""

    def health(self) -> dict[str, Any]:
        if self.fake:
            return {"status": "ok", "devices": [], "model": "fake"}
        try:
            import openvino as ov

            devices = ov.Core().available_devices
            return {"status": "ok", "devices": devices, "model": self.xml}
        except Exception as exc:  # pragma: no cover
            return {"status": "degraded", "error": str(exc), "model": self.xml or ""}

    def generate(self, prompt: str, max_new_tokens: int = 64) -> str:
        if self.fake or self._compiled is None:
            return f"[FAKE:{self.device}] {prompt} ... ({max_new_tokens})"
        # Placeholder inference logic. Add tokenizer/inference/detokenizer here.
        return f"[OV:{self.device}] {prompt} ... ({max_new_tokens})"
