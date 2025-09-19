"""Patch the CI workflow to collect and upload coverage reports."""
from __future__ import annotations

from pathlib import Path


def main() -> None:
    ci_path = Path(".github/workflows/ci.yml")
    if not ci_path.is_file():
        raise SystemExit("ci workflow not found")

    content = ci_path.read_text(encoding="utf-8")

    if "pytest -q --cov" not in content:
        content = content.replace("pytest -q", "pytest -q --cov=.")

    artifact_snippet = (
        "      - uses: actions/upload-artifact@v4\n"
        "        with:\n"
        "          name: coverage-report\n"
        "          path: htmlcov\n"
    )
    if "actions/upload-artifact" not in content:
        content = content.replace(
            "pytest -q --cov=.",
            "pytest -q --cov=. --cov-report=term-missing --cov-report=html\n" + artifact_snippet,
        )

    if "pip install pytest-cov" not in content and "pip install -r requirements.txt" in content:
        content = content.replace(
            "pip install -r requirements.txt",
            "pip install -r requirements.txt\n      - run: pip install pytest-cov",
        )

    ci_path.write_text(content, encoding="utf-8")
    print(f"patched: {ci_path}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
