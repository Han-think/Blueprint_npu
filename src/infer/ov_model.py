from __future__ import annotations

import glob
import os
from typing import Any, Dict


class OVRunner:
    def __init__(self) -> None:
        self.xml = os.environ.get("OV_XML_PATH") or self._auto_find()
        self.device = os.environ.get("OV_DEVICE", "AUTO")
        self.fake = os.environ.get("ALLOW_FAKE_GEN") == "1" or not (
            self.xml and os.path.exists(self.xml)
        )
        self.core = None
        self.compiled = None
        if not self.fake:
            import openvino as ov

            self.core = ov.Core()
            self.compiled = self.core.compile_model(self.core.read_model(self.xml), self.device)

    def _auto_find(self) -> str:
        candidates = glob.glob("exports/**/*.xml", recursive=True)
        candidates += glob.glob("models/**/*.xml", recursive=True)
        candidates.append("exports/gpt_ov/openvino_model.xml")
        for path in candidates:
            if os.path.exists(path):
                return path
        return ""

    def health(self) -> Dict[str, Any]:
        try:
            import openvino as ov

            devices = ov.Core().available_devices
            model = "fake" if self.fake else self.xml
            return {"status": "ok", "devices": devices, "model": model}
        except Exception as exc:  # pragma: no cover - diagnostic path
            return {
                "status": "degraded",
                "error": str(exc),
                "model": "fake" if self.fake else self.xml,
            }

    def generate(self, prompt: str, max_new_tokens: int = 64) -> str:
        if self.fake:
            return f"[FAKE:{self.device}] {prompt} ... ({max_new_tokens})"
        # 실제 모델 로직을 연결할 자리. 템플릿에서는 에코 동작 유지.
        return f"[OV:{self.device}] {prompt} ... ({max_new_tokens})"
