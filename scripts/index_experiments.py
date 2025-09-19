from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path("data/experiments")
    root.mkdir(parents=True, exist_ok=True)
    print({"indexed": 0, "root": str(root)})


if __name__ == "__main__":
    main()
