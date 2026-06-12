"""Slug and branch derivation from git context."""

from __future__ import annotations

import subprocess
from pathlib import Path

from vague.sdk.core.logging import get_logger


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
    except Exception as e:
        get_logger().debug("get_slug: git remote lookup failed, falling back to cwd: %s", e)

    # Fallback: basename of the repo root (not cwd — a subdir would split the
    # project's state across slugs), then basename of cwd outside any repo.
    try:
        base = get_repo_root(Path(work_dir) if work_dir else None).name
        return base or "unknown"
    except Exception as e:
        get_logger().debug("get_slug: repo root basename failed, using 'unknown': %s", e)
        return "unknown"


def get_repo_root(cwd: Path | None = None) -> Path:
    """Repo toplevel for the current dir. Fallback: cwd itself."""
    work_dir = str(cwd) if cwd else None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=work_dir, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except Exception as e:
        get_logger().debug("get_repo_root: git rev-parse failed, falling back to cwd: %s", e)
    return cwd if cwd else Path.cwd()


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
    except Exception as e:
        get_logger().debug("get_branch: git branch lookup failed, using 'unknown': %s", e)
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
