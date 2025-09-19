import threading
import time
import uvicorn


TARGETS = [
    ("app.moo:app", 9007),
    ("app.moo2:app", 9015),
    ("app.moo3:app", 9019),
    ("app.assembly:app", 9005),
    ("app.geometry:app", 9008),
    ("app.results:app", 9018),
    ("app.verify:app", 9014),
    ("app.verify2:app", 9016),
    ("app.materials:app", 9017),
    ("app.meta:app", 9013),
    ("app.metrics:app", 9020),
]


def run(target: str, port: int):
    uvicorn.run(target, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    threads = []
    for module, port in TARGETS:
        thread = threading.Thread(target=run, args=(module, port), daemon=True)
        thread.start()
        threads.append(thread)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
