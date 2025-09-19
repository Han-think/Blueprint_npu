from __future__ import annotations

import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "scripts/bp.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode in {0, 1}

