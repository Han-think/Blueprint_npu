"""Run multiple FastAPI services locally for quick manual testing."""

from __future__ import annotations

import threading
import time
from typing import Tuple

import uvicorn

TARGETS: Tuple[Tuple[str, int], ...] = (
    ("app.moo:app", 9007),
    ("app.moo2:app", 9015),
    ("app.assembly:app", 9005),
    ("app.geometry:app", 9008),
    ("app.geometry2:app", 9012),
    ("app.meta:app", 9013),
    ("app.verify:app", 9014),
    ("app.verify2:app", 9016),
    ("app.materials:app", 9017),
    ("app.ascent:app", 9011),
    ("app.mission:app", 9010),
    ("app.results:app", 9018),
)


def _run(module: str, port: int) -> None:
    uvicorn.run(module, host="127.0.0.1", port=port, log_level="info")


def main() -> None:
    threads: list[threading.Thread] = []
    for module, port in TARGETS:
        thread = threading.Thread(target=_run, args=(module, port), daemon=True)
        thread.start()
        threads.append(thread)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

