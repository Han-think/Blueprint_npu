from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Optional


class OVRunner:
    """Lazy wrapper around OpenVINO GenAI text-generation models.

    The runner first tries to bootstrap an ``openvino_genai`` pipeline from
    ``OV_MODEL_DIR`` or the directory that contains ``OV_XML_PATH``.  When the
    GenAI package or model assets are not available it falls back to a simple
    echo implementation so that CI smoke tests can still exercise the API.
    """

    def __init__(self) -> None:
        self.device = os.environ.get("OV_DEVICE", "AUTO")
        os.environ.setdefault("OV_CACHE_DIR", ".ov_cache")

        self.model_dir = self._resolve_model_dir()
        self.xml = self._resolve_xml_path(self.model_dir)

        self.genai_model = None
        self.core = None
        self.compiled = None
        self.genai_config = None

        allow_fake = os.environ.get("ALLOW_FAKE_GEN", "0") == "1"
        xml_exists = bool(self.xml and os.path.exists(self.xml))
        self.fake = allow_fake or not xml_exists
        self.mode = "fake"

        if not self.fake and xml_exists:
            self._try_init_models()

    # ------------------------------------------------------------------
    # Helpers
    def _resolve_model_dir(self) -> Optional[str]:
        explicit = os.environ.get("OV_MODEL_DIR")
        if explicit:
            return explicit

        xml_from_env = os.environ.get("OV_XML_PATH")
        if xml_from_env:
            return str(Path(xml_from_env).resolve().parent)

        # Try to infer from exports/ or models/ folders
        for root in (Path("exports"), Path("models")):
            if root.exists():
                matches = list(root.rglob("*.xml"))
                if matches:
                    return str(matches[0].resolve().parent)
        return None

    def _resolve_xml_path(self, model_dir: Optional[str]) -> str:
        xml_env = os.environ.get("OV_XML_PATH")
        if xml_env:
            return xml_env
        if model_dir:
            hint = Path(model_dir)
            matches = list(hint.glob("*.xml"))
            if matches:
                return str(matches[0])
            matches = list(hint.rglob("*.xml"))
            if matches:
                return str(matches[0])
        return self._auto_find_xml()

    @staticmethod
    def _auto_find_xml() -> str:
        search_roots = ["exports", "models"]
        patterns = ["*.xml", os.path.join("**", "*.xml")]
        for root in search_roots:
            for pattern in patterns:
                matches = glob.glob(os.path.join(root, pattern), recursive=True)
                if matches:
                    return matches[0]
        return ""

    def _try_init_models(self) -> None:
        # Try OpenVINO GenAI first – it provides tokenisation utilities
        model_dir = self.model_dir or (Path(self.xml).resolve().parent if self.xml else None)
        if model_dir:
            try:
                from openvino_genai import GenerationConfig, TextGenerationModel

                self.genai_model = TextGenerationModel(model_dir, device_name=self.device)
                self.genai_config = GenerationConfig()
                self.mode = "genai"
                return
            except Exception:
                self.genai_model = None

        # Fallback: keep a compiled model around (no tokenizer integration yet)
        try:
            import openvino as ov

            self.core = ov.Core()
            model = self.core.read_model(self.xml)
            self.compiled = self.core.compile_model(model, self.device)
            self.mode = "runtime"
        except Exception:
            self.compiled = None
            self.core = None
            self.fake = True
            self.mode = "fake"

    # ------------------------------------------------------------------
    # Public API
    def health(self) -> dict:
        if self.fake:
            status = "ok" if os.environ.get("ALLOW_FAKE_GEN", "0") == "1" else "degraded"
            return {
                "status": status,
                "model": "fake",
                "device": self.device,
                "xml": self.xml or "",
                "mode": "fake",
            }
        info = {"status": "ok", "device": self.device, "xml": self.xml or "", "mode": self.mode}
        try:
            import openvino as ov

            info["available_devices"] = ov.Core().available_devices
        except Exception as exc:  # pragma: no cover - defensive
            info["status"] = "degraded"
            info["error"] = str(exc)
        return info

    def generate(self, prompt: str, max_new_tokens: int = 64) -> str:
        if self.fake:
            return f"[FAKE:{self.device}] {prompt} ... ({max_new_tokens})"

        if self.genai_model is not None:
            try:
                config = self.genai_config
                if config is None:
                    from openvino_genai import GenerationConfig

                    config = GenerationConfig()
                config.max_new_tokens = max_new_tokens
                outputs = self.genai_model.generate(prompt, generation_config=config)
                if isinstance(outputs, (list, tuple)) and outputs:
                    return outputs[0]
                return str(outputs)
            except Exception:
                return self._runtime_generate(prompt, max_new_tokens)

        # Compiled-model fallback – tokenizer integration is model specific.
        return self._runtime_generate(prompt, max_new_tokens)

    def _runtime_generate(self, prompt: str, max_new_tokens: int) -> str:
        """Best-effort text if only the compiled model is available.

        Without task-specific tokenisers we cannot decode logits into text, so we
        surface a deterministic stub that still indicates the request completed
        on the OpenVINO runtime.
        """

        return f"[OV:{self.device}] {prompt} ... ({max_new_tokens})"
