codex/initialize-npu-inference-template-ys4nnv
import threading
import time

import requests
import uvicorn

import requests, threading, time, uvicorn
main
from app.main import app


def run():
    uvicorn.run(app, host="127.0.0.1", port=9001)


if __name__ == "__main__":
    th = threading.Thread(target=run, daemon=True)
    th.start()
    time.sleep(2)
    print(requests.get("http://127.0.0.1:9001/health", timeout=5).json())
