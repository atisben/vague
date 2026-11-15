"""Slug and branch derivation from git context."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from vague import git


def _remote_slug(work_dir: Path) -> str:
    """Slug from the `origin` remote URL, or "" when there is none."""
    url = git.run("remote", "get-url", "origin", cwd=work_dir)
    return _parse_remote_to_slug(url) if url else ""


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
    # check=False: in a repo with no commits git exits 128 on HEAD but has already printed the three paths.
    output = git.run("rev-parse", "--path-format=absolute", "--show-toplevel", "--git-dir",
                     "--git-common-dir", "--symbolic-full-name", "HEAD", cwd=cwd, check=False)
    lines = (output or "").splitlines()
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
        slug = _remote_slug(context.root)
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


def _parse_remote_to_slug(url: str) -> str:
    """Parse a git remote URL into owner-repo format."""
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
