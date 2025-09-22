from __future__ import annotations
 codex/initialize-npu-inference-template-v1n7c2

from pathlib import Path
from typing import List, Optional

import numpy as np




import numpy as np

from pathlib import Path
from typing import Optional

codex/initialize-npu-inference-template-ys4nnv


main
 main
class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
 codex/initialize-npu-inference-template-v1n7c2
        self.compiled = None
        if not fake:
            self._try_load_openvino()

    def _try_load_openvino(self) -> None:
        xml = Path("models/surrogate.xml")
        bin_file = Path("models/surrogate.bin")
        if not (xml.exists() and bin_file.exists()):

codex/initialize-npu-inference-template-ys4nnv
        self.compiled = None  # OpenVINO runtime
        self.onnx_sess = None  # ONNX Runtime session
        self.lin_model = None  # NPZ linear/poly fallback
        self._lin_w: Optional[np.ndarray] = None
        self._lin_deg = 0

        if self.fake:
            return

        # 1) OpenVINO
        self._try_load_openvino()
        if self.compiled is not None:
            return

        # 2) ONNX Runtime
        self._try_load_onnx()
        if self.onnx_sess is not None:
            return

        # 3) NPZ weights
        self._try_load_npz()

    # -------- Backend loaders --------
    def _try_load_openvino(self) -> None:

        self.compiled = None
        self.lin_model = False
        self._lin_w: Optional[np.ndarray] = None
        self._lin_deg: int = 1
        if not fake:
            self._try_load_openvino()
        self._load_npz_fallback()

    def _try_load_openvino(self):
main
        xml = Path("models/surrogate.xml")
        binf = Path("models/surrogate.bin")
        if not (xml.exists() and binf.exists()):
 main
            self.compiled = None
            self.device_selected = "CPU"
            return
        try:
            from openvino.runtime import Core
 codex/initialize-npu-inference-template-v1n7c2

            core = Core()
            preferred = [d for d in (self.device_hint, "NPU", "GPU", "CPU") if d]
            chosen = next((d for d in preferred if d in core.available_devices), "CPU")
            model = core.read_model(model=str(xml))
            self.compiled = core.compile_model(model=model, device_name=chosen)
            self.device_selected = chosen

codex/initialize-npu-inference-template-ys4nnv

            core = Core()
            pref = ["NPU", "GPU", "CPU"]

            core = Core()
            pref = ["NPU","GPU","CPU"]
main
            if self.device_hint and self.device_hint in pref:
                pref = [self.device_hint] + [d for d in pref if d != self.device_hint]
            chosen = next((d for d in pref if d in core.available_devices), "CPU")
            self.compiled = core.compile_model(model=str(xml), device_name=chosen)
codex/initialize-npu-inference-template-ys4nnv
            self.device_selected = f"OV:{chosen}"

main
 main
        except Exception:
            self.compiled = None
            self.device_selected = "CPU"

 codex/initialize-npu-inference-template-v1n7c2
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

codex/initialize-npu-inference-template-ys4nnv
    def _try_load_onnx(self) -> None:
        onnxf = Path("models/surrogate.onnx")
        if not onnxf.exists():
            self.onnx_sess = None
            return
        try:
            import onnxruntime as ort


            providers = ["CPUExecutionProvider"]
            self.onnx_sess = ort.InferenceSession(str(onnxf), providers=providers)
            self._onnx_input = self.onnx_sess.get_inputs()[0].name
            self._onnx_output = self.onnx_sess.get_outputs()[0].name
            self.device_selected = "ONNX:CPU"
        except Exception:
            self.onnx_sess = None

    def _try_load_npz(self) -> None:
        try:
            import numpy as _np

        except Exception:
            return
        npz = Path("models/surrogate.npz")
        if not npz.exists():
            return
        try:
            nz = _np.load(npz)
            self._lin_w = nz["w"]
            self._lin_deg = int(nz["deg"])
            self.lin_model = True
            self.device_selected = "NPZ"
        except Exception:
            self.lin_model = None
            self._lin_w = None
            self._lin_deg = 0

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
main

    def _poly_features(self, X: np.ndarray) -> np.ndarray:
        n, d = X.shape
        feats = [np.ones((n, 1)), X]
        if self._lin_deg >= 2:
codex/initialize-npu-inference-template-ys4nnv
            feats.append(X**2)

            feats.append(X ** 2)
main
            for i in range(d):
                for j in range(i + 1, d):
                    feats.append(X[:, i : i + 1] * X[:, j : j + 1])
        if self._lin_deg >= 3:
codex/initialize-npu-inference-template-ys4nnv
            feats.append(X**3)
        return np.hstack(feats)

    # -------- Prediction --------
    def predict(self, designs: list[list[float]]) -> list[float]:
        X = np.asarray(designs, dtype=float)

        if (not self.fake) and (self.compiled is not None):
            try:
                res = self.compiled([X.astype(np.float32)])[self.compiled.outputs[0]]
                return np.asarray(res).ravel().astype(float).tolist()
            except Exception:
                pass

        if (not self.fake) and (self.onnx_sess is not None):
            try:
                inp = {self._onnx_input: X.astype(np.float32)}
                res = self.onnx_sess.run([self._onnx_output], inp)[0]
                return np.asarray(res).ravel().astype(float).tolist()
            except Exception:
                pass

        if (not self.fake) and self.lin_model and self._lin_w is not None:
            try:
                Phi = self._poly_features(X)
                y = Phi.dot(self._lin_w)
                return np.asarray(y).ravel().astype(float).tolist()
            except Exception:
                pass

        y = 1.0 - np.sum(X * X, axis=1)
        return y.tolist()

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
main
 main
