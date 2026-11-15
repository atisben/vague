"""The one way vague spawns git."""

from __future__ import annotations

import subprocess
from pathlib import Path

from vague.sdk.core.logging import get_logger


def run(*args: str, cwd: Path | str | None = None, timeout: float = 5, check: bool = True) -> str | None:
    """Stdout of `git <args>`, stripped, or None when git is missing, slow, or (with check) exits non-zero.

    `check=False` keeps the output of a failing command: `rev-parse` in a repo with no commits
    exits 128 yet has already printed the paths a caller needs.
    """
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError) as e:
        get_logger().debug("git %s failed in %s: %s", args, cwd, e)
        return None
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()
