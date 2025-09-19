 codex/initialize-npu-inference-template-v1n7c2
from __future__ import annotations

import os

"""Simple API key guard for optional request authentication."""

from __future__ import annotations

import os

 main
from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
 codex/initialize-npu-inference-template-v1n7c2

    """Raise if the provided X-API-KEY header does not match the expected value."""

 main
    expected = os.getenv("API_KEY")
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid api key")
