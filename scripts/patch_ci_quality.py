"""Patch CI workflow to add Ruff and mypy quality checks."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    workflow = Path(".github/workflows/ci.yml")
    content = workflow.read_text(encoding="utf-8")
    if "ruff" in content:
        print("already patched")
        return
    content = content.replace(
        "pip install -r requirements.txt",
        "pip install -r requirements.txt\n      - run: pip install ruff mypy",
    )
    mypy_targets = (
        "mypy --version && mypy "
        "app/security.py app/mission.py app/ascent.py app/geometry2.py "
        "scripts/index_experiments.py proof/index_db.py"
    )
    content = content.replace(
        "pytest -q",
        f"pytest -q\n      - run: ruff check .\n      - run: {mypy_targets}",
    )
    workflow.write_text(content, encoding="utf-8")
    print("patched:", workflow)


if __name__ == "__main__":
    main()
