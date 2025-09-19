import requests
import threading
import time

import uvicorn

from app.main import app


def _run():
    uvicorn.run(app, host="127.0.0.1", port=9001)


if __name__ == "__main__":
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(2)
    response = requests.get("http://127.0.0.1:9001/health", timeout=5)
    print(response.json())
