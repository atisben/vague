"""Slug and branch derivation from git context."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

from vague.sdk.core.logging import get_logger


def _remote_slug(work_dir: str | None) -> str:
    """Slug from the `origin` remote URL, or "" when there is none."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, cwd=work_dir, timeout=5
        )
        if result.returncode == 0:
            return _parse_remote_to_slug(result.stdout.strip())
    except Exception as e:
        get_logger().debug("get_slug: git remote lookup failed, falling back to cwd: %s", e)
    return ""


def get_slug(cwd: Path | None = None) -> str:
    """Owner-repo slug from the git remote, else the main checkout's folder name, else cwd's.

    Same rule as get_scope, so a remote-less worktree shares its main checkout's slug.
    """
    return get_repo_slug(context=get_git_context(cwd=cwd))


class GitContext(NamedTuple):
    """Where a directory sits in git. Paths from git are symlink-resolved."""

    in_repo: bool
    root: Path
    main_root: Path
    is_worktree: bool
    branch: str


def get_git_context(cwd: Path | None = None) -> GitContext:
    """Root, main checkout, worktree flag and branch in one git process.

    Outside a repo, or on any git failure, root and main_root are cwd itself and
    the branch is "unknown". Never raises.
    """
    start = cwd if cwd else Path.cwd()
    fallback = GitContext(in_repo=False, root=start, main_root=start, is_worktree=False,
                          branch="unknown")
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-dir",
             "--git-common-dir", "--symbolic-full-name", "HEAD"],
            capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=5
        )
    except Exception as e:
        get_logger().debug("get_git_context: git rev-parse failed, falling back to cwd: %s", e)
        return fallback

    # Do not check the return code: in a repo with no commits git exits 128 on
    # HEAD but has already printed the three paths.
    lines = result.stdout.splitlines()
    if len(lines) < 3:
        return fallback
    root, git_dir, common_dir = Path(lines[0]), Path(lines[1]), Path(lines[2])
    head = lines[3] if len(lines) > 3 else ""
    branch = head.removeprefix("refs/heads/") if head.startswith("refs/heads/") else "unknown"
    is_worktree = git_dir != common_dir
    # A linked worktree's common dir is <main>/.git. Bare repos and submodules
    # have a differently named common dir, so there is no main checkout to name.
    main_root = common_dir.parent if is_worktree and common_dir.name == ".git" else root
    return GitContext(in_repo=True, root=root, main_root=main_root, is_worktree=is_worktree,
                      branch=branch)


def get_repo_slug(context: GitContext) -> str:
    """Slug from the remote, else the main checkout's folder name, so every worktree of a repo shares it."""
    if context.in_repo:
        slug = _remote_slug(str(context.root))
        if slug:
            return slug
    return context.main_root.name or "unknown"


def get_scope(cwd: Path | None = None, use_global: bool = False) -> str | None:
    """Memory scope for a directory, or None in $HOME or `/`.

    A memory logged from the home folder or the filesystem root would land in a
    scope named after the user or nothing, so the caller refuses instead.
    """
    if use_global:
        return "global"
    start = (cwd or Path.cwd()).resolve()
    if start in (Path.home().resolve(), Path("/")):
        return None
    return get_repo_slug(context=get_git_context(cwd=start))


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
