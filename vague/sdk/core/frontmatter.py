"""Atomic frontmatter read/write with file locking."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Callable, Iterator

import frontmatter


class FrontmatterError(Exception):
    pass


@contextlib.contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock around a read-modify-write of `path`.

    Lets concurrent processes (e.g. parallel subagents appending learnings)
    serialize their updates instead of clobbering each other. The lock file is
    intentionally NOT unlinked on release: removing it would let two processes
    lock different inodes and defeat the lock entirely.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(str(path) + ".lock")
    lock_fd = open(lock_path, "w")
    try:
        _flock(lock_fd, exclusive=True)
        yield
    finally:
        _flock(lock_fd, exclusive=False)
        lock_fd.close()


def _atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` atomically via a per-process temp file."""
    tmp_path = path.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


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
    with file_lock(path):
        _atomic_write(path, content)


def update_md(path: Path, updater: Callable[[dict], dict]) -> None:
    """Read-modify-write with lock held throughout."""
    with file_lock(path):
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
        _atomic_write(path, content)


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
