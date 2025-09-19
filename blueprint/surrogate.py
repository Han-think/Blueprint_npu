from __future__ import annotations
import numpy as np
from pathlib import Path
from typing import Optional


class Surrogate:
    def __init__(self, fake: bool = False, device: Optional[str] = None):
        self.fake = fake
        self.device_hint = device
        self.device_selected = "FAKE" if fake else "CPU"
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
        xml = Path("models/surrogate.xml")
        binf = Path("models/surrogate.bin")
        if not (xml.exists() and binf.exists()):
            self.compiled = None
            self.device_selected = "CPU"
            return
        try:
            from openvino.runtime import Core

            core = Core()
            pref = ["NPU", "GPU", "CPU"]
            if self.device_hint and self.device_hint in pref:
                pref = [self.device_hint] + [d for d in pref if d != self.device_hint]
            chosen = next((d for d in pref if d in core.available_devices), "CPU")
            self.compiled = core.compile_model(model=str(xml), device_name=chosen)
            self.device_selected = f"OV:{chosen}"
        except Exception:
            self.compiled = None
            self.device_selected = "CPU"

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

    def _poly_features(self, X: np.ndarray) -> np.ndarray:
        n, d = X.shape
        feats = [np.ones((n, 1)), X]
        if self._lin_deg >= 2:
            feats.append(X**2)
            for i in range(d):
                for j in range(i + 1, d):
                    feats.append(X[:, i : i + 1] * X[:, j : j + 1])
        if self._lin_deg >= 3:
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
