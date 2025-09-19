from __future__ import annotations

import json
import threading
import json
import threading
import time
from pathlib import Path

import requests


def ensure_api_smoke() -> str:
    path = Path("scripts/api_smoke.py")
    if path.is_file():
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import requests, threading, time, uvicorn\n"
        "from app.main import app\n"
        "def run(): uvicorn.run(app, host='127.0.0.1', port=9001)\n"
        "th=threading.Thread(target=run, daemon=True); th.start()\n"
        "time.sleep(2)\n"
        "print(requests.get('http://127.0.0.1:9001/health', timeout=5).json())\n",
        encoding="utf-8",
    )
    return str(path)


def start_uvicorn(import_str: str, port: int):
    import uvicorn

    def _run():
        uvicorn.run(import_str, host="127.0.0.1", port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def wait_http(url: str, timeout_s: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    summary = {"steps": []}
    api_smoke_path = ensure_api_smoke()
    summary["steps"].append({"ensure_api_smoke": api_smoke_path})

    thread_moo = start_uvicorn("app.moo3:app", 9019)
    if not wait_http("http://127.0.0.1:9019/moo3/health", 25):
        print(json.dumps({"ok": False, "error": "moo3 not responding", "summary": summary}, ensure_ascii=False, indent=2))
        return
    summary["steps"].append({"moo3_health": True})

    payload = {"samples": 128, "generations": 10, "topk": 16}
    response = requests.post("http://127.0.0.1:9019/moo3/rocket", json=payload, timeout=300)
    response.raise_for_status()
    pareto = response.json()
    Path("data/pareto").mkdir(parents=True, exist_ok=True)
    pareto_path = Path("data/pareto/latest.json")
    pareto_path.write_text(json.dumps(pareto, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["steps"].append({"pareto_saved": str(pareto_path), "count": len(pareto.get("top", []))})

    thread_results = start_uvicorn("app.results:app", 9018)
    if not wait_http("http://127.0.0.1:9018/results/health", 20):
        print(json.dumps({"ok": False, "error": "results api not responding", "summary": summary}, ensure_ascii=False, indent=2))
        return
    summary["steps"].append({"results_health": True})

    Path("data/geometry").mkdir(parents=True, exist_ok=True)
    stl_path = Path("data/geometry/latest_nozzle_0.stl")
    query = "http://127.0.0.1:9018/results/topstl?name=latest.json&index=0&seg=96"
    stl_response = requests.get(query, timeout=60)
    if stl_response.status_code == 200 and stl_response.headers.get("content-type", "").startswith("model/stl"):
        stl_path.write_bytes(stl_response.content)
        summary["steps"].append({"stl_saved": str(stl_path), "bytes": len(stl_response.content)})
    else:
        summary["steps"].append({"stl_saved": None, "status": stl_response.status_code})

    print(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
