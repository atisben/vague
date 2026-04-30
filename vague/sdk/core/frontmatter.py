"""Atomic frontmatter read/write with file locking."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

import frontmatter


class FrontmatterError(Exception):
    pass


def read_md(path: Path) -> dict:
    """Read frontmatter from a .md file. Returns {} if file doesn't exist."""
    if not path.exists():
        return {}
    try:
        post = frontmatter.load(str(path))
        return dict(post.metadata)
    except Exception as e:
        raise FrontmatterError(f"Failed to parse frontmatter in {path}: {e}") from e


def write_md(path: Path, data: dict, body: str = "") -> None:
    """Write frontmatter + body atomically. Creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **data)
    content = frontmatter.dumps(post)

    tmp_path = path.with_suffix(".tmp")
    lock_fd = None
    try:
        lock_fd = open(str(path) + ".lock", "w")
        _flock(lock_fd, exclusive=True)
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if lock_fd is not None:
            _flock(lock_fd, exclusive=False)
            lock_fd.close()
            try:
                Path(str(path) + ".lock").unlink(missing_ok=True)
            except OSError:
                pass


def update_md(path: Path, updater: Callable[[dict], dict]) -> None:
    """Read-modify-write with lock held throughout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = None
    try:
        lock_fd = open(str(path) + ".lock", "w")
        _flock(lock_fd, exclusive=True)

        if path.exists():
            try:
                post = frontmatter.load(str(path))
                existing = dict(post.metadata)
                body = post.content
            except Exception as e:
                raise FrontmatterError(f"Failed to parse frontmatter in {path}: {e}") from e
        else:
            existing = {}
            body = ""

        updated = updater(existing)
        new_post = frontmatter.Post(body, **updated)
        content = frontmatter.dumps(new_post)

        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if lock_fd is not None:
            _flock(lock_fd, exclusive=False)
            lock_fd.close()
            try:
                Path(str(path) + ".lock").unlink(missing_ok=True)
            except OSError:
                pass


def _flock(fd, exclusive: bool) -> None:
    """Advisory file lock. No-op on Windows."""
    if sys.platform == "win32":
        return
    try:
        import fcntl
        flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_UN
        fcntl.flock(fd.fileno(), flag)
    except (ImportError, OSError):
        pass
