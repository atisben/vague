"""Atomic git commit using GitPython."""

from __future__ import annotations

from pathlib import Path

NOTHING_TO_COMMIT = "nothing-to-commit"


def atomic_commit(message: str, files: list[str], cwd: Path | None = None) -> str:
    """Stage files, commit with GitPython. Returns commit SHA or 'nothing-to-commit'."""
    try:
        import git as gitpython
        repo = gitpython.Repo(str(cwd) if cwd else ".", search_parent_directories=True)

        for f in files:
            repo.index.add([f])

        if not repo.index.diff("HEAD") and not repo.index.diff(None):
            return NOTHING_TO_COMMIT

        commit = repo.index.commit(message)
        return commit.hexsha
    except Exception as e:
        if "nothing to commit" in str(e).lower():
            return NOTHING_TO_COMMIT
        raise
