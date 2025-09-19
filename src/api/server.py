from __future__ import annotations

import time
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.infer.ov_model import OVRunner


app = FastAPI(title="npu-infer-template", version="0.1.0")
_runner = OVRunner()


class InferReq(BaseModel):
    prompt: str = Field("Hello NPU", min_length=1, max_length=2048)
    max_new_tokens: int = Field(64, ge=1, le=4096)


@app.get("/health")
def health() -> dict[str, object]:
    return _runner.health()


@app.post("/v1/infer")
def infer(req: InferReq) -> dict[str, object]:
    t0 = time.time()
    result = _runner.generate(req.prompt, req.max_new_tokens)
    return {"result": result, "elapsed_ms": int((time.time() - t0) * 1000)}
