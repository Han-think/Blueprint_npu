import requests
import threading
import time
import uvicorn
from app.main import app

def run():
    uvicorn.run(app, host="127.0.0.1", port=9001)


if __name__ == "__main__":
    th = threading.Thread(target=run, daemon=True)
    th.start()
    time.sleep(2)
    print(requests.get("http://127.0.0.1:9001/health", timeout=5).json())
