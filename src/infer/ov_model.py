from __future__ import annotations

import glob
import os
from typing import Optional


class OVRunner:
    def __init__(self) -> None:
        self.xml = os.environ.get("OV_XML_PATH") or self._auto_find()
        self.device = os.environ.get("OV_DEVICE", "AUTO")
        self.core = None
        self.compiled = None
        xml_exists = bool(self.xml and os.path.exists(self.xml))
        self.fake = os.environ.get("ALLOW_FAKE_GEN", "0") == "1" or not xml_exists
        if not self.fake and xml_exists:
            try:
                import openvino as ov

                self.core = ov.Core()
                model = self.core.read_model(self.xml)
                self.compiled = self.core.compile_model(model, self.device)
            except Exception:
                self.fake = True
                self.core = None
                self.compiled = None

    def _auto_find(self) -> str:
        search_roots = ["exports", "models"]
        patterns = ["*.xml", os.path.join("**", "*.xml")]
        for root in search_roots:
            for pattern in patterns:
                matches = glob.glob(os.path.join(root, pattern), recursive=True)
                if matches:
                    return matches[0]
        # fallback default hint to avoid empty string issues downstream
        default_path = "exports/gpt_ov/openvino_model.xml"
        return default_path if os.path.exists(default_path) else ""

    def health(self) -> dict:
        if self.fake:
            return {"status": "ok", "model": "fake", "device": self.device}
        try:
            import openvino as ov

            devices = ov.Core().available_devices
        except Exception as exc:  # pragma: no cover - protective
            return {"status": "degraded", "error": str(exc), "model": self.xml or ""}
        return {"status": "ok", "devices": devices, "model": self.xml}

    def generate(self, prompt: str, max_new_tokens: int = 64) -> str:
        if self.fake or not self.compiled:
            return f"[FAKE:{self.device}] {prompt} ... ({max_new_tokens})"
        # Template placeholder: user should integrate tokenizer/decoder here.
        return f"[OV:{self.device}] {prompt} ... ({max_new_tokens})"
