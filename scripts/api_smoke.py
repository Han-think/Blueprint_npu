import threading
import time

import requests
import uvicorn


def _run() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=9001, log_level="warning")


def main() -> None:
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(2)
    resp = requests.get("http://127.0.0.1:9001/health", timeout=5)
    print(resp.json())


if __name__ == "__main__":
    main()
