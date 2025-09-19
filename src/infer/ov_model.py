from __future__ import annotations

import glob

import os



class OVRunner:
    def __init__(self):
        self.xml = os.environ.get("OV_XML_PATH") or self._auto_find()
        self.device = os.environ.get("OV_DEVICE", "AUTO")
        self.fake = os.environ.get("ALLOW_FAKE_GEN") == "1" or not os.path.exists(self.xml)
        if not self.fake:
            import openvino as ov


            self.core = ov.Core()
            self.compiled = self.core.compile_model(self.core.read_model(self.xml), self.device)

    def _auto_find(self) -> str:
        c1 = glob.glob("exports/**/*.xml", recursive=True)
        c2 = glob.glob("models/**/*.xml", recursive=True)
        return (c1 + c2 + ["exports/gpt_ov/openvino_model.xml"])[0]

    def health(self):
        try:
            import openvino as ov


            devs = ov.Core().available_devices
            return {"status": "ok", "devices": devs, "model": ("fake" if self.fake else self.xml)}
        except Exception as e:
            return {"status": "degraded", "error": str(e), "model": ("fake" if self.fake else self.xml)}

    def generate(self, prompt: str, max_new_tokens: int = 64) -> str:
        if self.fake:
            return f"[FAKE:{self.device}] {prompt} ... ({max_new_tokens})"
        # 여기에 모델별 전처리/후처리 붙이면 됨. 템플릿은 에코형으로 둠.
        # 예: tokenizer(prompt) → infer → detokenize
        return f"[OV:{self.device}] {prompt} ... ({max_new_tokens})"
