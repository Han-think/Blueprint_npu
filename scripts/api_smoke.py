 codex/initialize-npu-inference-template-v1n7c2
import requests
import threading
import time

import uvicorn

from app.main import app


def _run():

codex/initialize-npu-inference-template-ys4nnv
import threading
import time

import requests
import uvicorn

import requests, threading, time, uvicorn
main
from app.main import app


def run():
 main
    uvicorn.run(app, host="127.0.0.1", port=9001)


if __name__ == "__main__":
 codex/initialize-npu-inference-template-v1n7c2
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(2)
    response = requests.get("http://127.0.0.1:9001/health", timeout=5)
    print(response.json())

    th = threading.Thread(target=run, daemon=True)
    th.start()
    time.sleep(2)
    print(requests.get("http://127.0.0.1:9001/health", timeout=5).json())
 main
