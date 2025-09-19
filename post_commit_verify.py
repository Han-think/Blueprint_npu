from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import requests
import uvicorn


def start_uvicorn(import_str: str, port: int) -> threading.Thread:
    def _run() -> None:
        uvicorn.run(import_str, host="127.0.0.1", port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def wait_http(url: str, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    summary: dict[str, list[dict[str, object]]] = {"steps": []}
    start_uvicorn("src.api.server:app", 9100)
    ok = wait_http("http://127.0.0.1:9100/health", 20)
    summary["steps"].append({"health": ok})
    if not ok:
        print(json.dumps({"ok": False, "summary": summary}, ensure_ascii=False, indent=2))
        return
    resp = requests.post(
        "http://127.0.0.1:9100/v1/infer",
        json={"prompt": "ping", "max_new_tokens": 8},
        timeout=30,
    )
    summary["steps"].append({"infer_status": resp.status_code})
    Path("out.json").write_text(resp.text, encoding="utf-8")
    print(json.dumps({"ok": resp.ok, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
