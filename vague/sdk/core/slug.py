"""Slug and branch derivation from git context."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_slug(cwd: Path | None = None) -> str:
    """Derive owner-repo slug from git remote. Fallback: basename of cwd."""
    work_dir = str(cwd) if cwd else None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=work_dir, timeout=5
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            slug = _parse_remote_to_slug(url)
            if slug:
                return slug
    except Exception:
        pass

    # Fallback to basename of cwd
    try:
        base = Path(work_dir).name if work_dir else Path.cwd().name
        return base or "unknown"
    except Exception:
        return "unknown"


def get_branch(cwd: Path | None = None) -> str:
    """Get current git branch. Fallback: 'unknown'."""
    work_dir = str(cwd) if cwd else None
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=work_dir, timeout=5
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                return branch
    except Exception:
        pass
    return "unknown"


def _parse_remote_to_slug(url: str) -> str:
    """Parse a git remote URL into owner-repo format."""
    import re
    url = url.strip()
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    # SSH: git@github.com:owner/repo
    m = re.match(r"git@[^:]+:(.+)", url)
    if m:
        path = m.group(1)
        return path.replace("/", "-")
    # HTTPS: https://github.com/owner/repo
    m = re.match(r"https?://[^/]+/(.+)", url)
    if m:
        path = m.group(1)
        return path.replace("/", "-")
    return ""
