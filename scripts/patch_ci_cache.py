from __future__ import annotations

from pathlib import Path

CI_PATH = Path(".github/workflows/ci.yml")
content = CI_PATH.read_text(encoding="utf-8")

if "actions/cache" not in content:
    cache_block = """      - uses: actions/cache@v4\n        with:\n          path: ~/.cache/pip\n          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}\n          restore-keys: |\n            ${{ runner.os }}-pip-\n"""
    content = content.replace(
        "      - run: python -m pip install -U pip",
        cache_block + "      - run: python -m pip install -U pip",
        1,
    )
    CI_PATH.write_text(content, encoding="utf-8")
    print(f"patched: {CI_PATH}")
else:
    print("cache step already present")
